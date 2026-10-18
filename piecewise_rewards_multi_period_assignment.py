import time

import pandas as pd
from ortools.linear_solver import pywraplp
from ortools.linear_solver.pywraplp import Solver

from lib.Account import Account
from lib.Prices import LivePrices
from lib.Skills import Skills
from lib.ProductionTask import Task

"""
instead of tasks having flat rewards tasks have a production and consumption dict of what they produce/consume per period
rewards for production fall off and penalty for consumption increase 
as the system wide impact approaches a certain portion of the market volume
"""


class MultiPeriodAssignmentModel:
    def __init__(self, periods, workforce, tasks):
        # just trust types
        self.periods = periods
        self.workforce = workforce
        self.tasks = tasks

        self.skill_names = tuple(vars(tasks[0].skill_rewards))

        self.task_assignments = {}
        self.skill_assignments = {}
        # set up constraints in constructor
        self.solver = pywraplp.Solver.CreateSolver("SCIP")
        if not self.solver:
            raise RuntimeError('Solver not available')

        self.items = set()
        for task in self.tasks:
            self.items.update(task.production)
            self.items.update(task.consumption)

        # grab liveprices volume
        self.volumes = {}
        self.lp = LivePrices()
        for item_id in self.items:
            vol = self.lp.get_volume(item_id)
            print(f"Item {id} volume: {vol}")
            # div 24 because 1 period is 1 hour in our model and lookup is 24h
            self.volumes[item_id] = vol / 24

        self.sys_wide_net = {}
        self.sys_wide_production = {}
        self.sys_wide_consumption = {}

        for item in self.items:
            tier_capacity = 0.1 * self.volumes[item]
            # production constraints apply to system wide production in a period
            for t in range(self.periods):
                self.sys_wide_net[item, t] = self.solver.NumVar(
                    -self.solver.infinity(), self.solver.infinity(), f"system_wide_net_{item}_{t}"
                )
                # 3 tiers, 2 being 10% volume and 3rd being 0 reward and infinite capacity
                for tier in range(3):
                    upper = tier_capacity if tier < 2 else self.solver.infinity()

                    self.sys_wide_production[item, t, tier] = self.solver.NumVar(
                        0, upper, f"sys_wide_production_{item}_{t}_{tier}"
                    )
                    self.sys_wide_consumption[item, t, tier] = self.solver.NumVar(
                        0, upper, f"sys_wide_consumption_{item}_{t}_{tier}"
                    )

                # net production must match that of the assignments
                self.solver.Add(
                    self.sys_wide_net[item, t] == self.solver.Sum(
                        (task.production.get(item, 0) - task.consumption.get(item, 0))
                        * self.task_assignments[w, j, t]
                        for w in range(len(workforce))
                        for j, task in enumerate(self.tasks)
                    )
                )
                # net production and gross must be balanced
                self.solver.Add(
                    self.sys_wide_net[item, t]
                    == self.solver.Sum(self.sys_wide_production[item, t, tier] for tier in range(3))
                    - self.solver.Sum(self.sys_wide_consumption[item, t, tier] for tier in range(3))
                )

        # eligibility decisions
        for w in range(len(self.workforce)):
            for j in range(len(tasks)):
                for t in range(periods + 1):
                    self.task_assignments[w, j, t] = self.solver.IntVar(0, 1, f"Decision {w}_{j}_{t}")
            for skill in self.skill_names:
                # need +1 so skill constraint keeps for the end state
                for t in range(periods + 1):
                    self.skill_assignments[w, skill, t] = self.solver.NumVar(0, self.solver.infinity(),
                                                                             f"skill_{w}_{skill}_{t}")

        # set starting skill constraints
        for w, acc in enumerate(self.workforce):
            for skill in self.skill_names:
                self.solver.Add(
                    self.skill_assignments[w, skill, 0] == getattr(acc.skills, skill)
                )

        # one task per worker per period
        for w in range(len(self.workforce)):
            for t in range(self.periods):
                self.solver.Add(
                    self.solver.Sum(
                        self.task_assignments[w, j, t] for j in range(len(self.tasks))
                    ) <= 1
                )

        # constrain skills at t+1 to be t + actions
        for w in range(len(self.workforce)):
            for skill in self.skill_names:
                for t in range(self.periods):
                    self.solver.Add(
                        self.skill_assignments[w, skill, t + 1]
                        == self.skill_assignments[w, skill, t] + self.solver.Sum(
                            getattr(task.skill_rewards, skill)
                            * self.task_assignments[w, j, t] for j, task in enumerate(self.tasks)
                        )
                    )

        # constrain to a methods maximum
        for j, task in enumerate(self.tasks):
            for t in range(self.periods):
                self.solver.Add(
                    self.solver.Sum(
                        self.task_assignments[w, j, t] for w in range(len(self.workforce))
                    ) <= task.max_accounts
                )

        # all assignments have requirements
        for w in range(len(self.workforce)):
            for j, task in enumerate(self.tasks):
                for t in range(self.periods):
                    for skill in self.skill_names:
                        self.solver.Add(
                            self.skill_assignments[w, skill, t]
                            >= getattr(task.skill_requirements, skill) * self.task_assignments[w, j, t]
                        )

        # Team size constraint
        for j, task in enumerate(self.tasks):
            for t in range(self.periods):
                active = self.solver.IntVar(0, 1, f"TaskActiveInPeriod_{task}_{t}")

                team_size = self.solver.Sum(
                    self.task_assignments[w, j, t] for w in range(len(self.workforce))
                )

                self.solver.Add(team_size >= task.required_team_size * active)
                # when not active this forces team size to 0
                self.solver.Add(team_size <= len(self.workforce) * active)

        # we have 3 reward tiers, 100% price reward for 10% of volume, 80%, then very low
        production_multipliers = (1, 0.8, 0.30)
        # multipliers for system wide consumption each period
        consumption_multipliers = (1, 1.2, 2)

        # objective function
        self.solver.Maximize(
            self.solver.Sum(
                self.lp.get_low_price(item) * (
                    production_multipliers[tier] * self.sys_wide_production[item, t, tier]
                    - consumption_multipliers[tier] & self.sys_wide_consumption[item, t, tier]
                )
                for item in self.items for t in range(self.periods) for tier in range(3)
            )
        )

    def get_solver(self):
        return self.solver


# test jaun
accounts = []
for i in range(50):
    accounts.append(Account(f"Acc{i}"))

task_db = [
    # negative reward herblore training
    Task(
        "Herblore training",
        Skills(0, 0, 0),
        Skills(0, 15, 0),
        -100, 10
    ),
    # extremely high return high level
    Task(
        "Mixology",
        Skills(0, 60, 0),
        Skills(0, 0, 0),
        100_000, 12
    ),
    # mining training
    Task(
        "Mining lowlvl",
        Skills(0, 0, 0),
        Skills(1, 0, 0),
        0, 100_000
    ),
    # higher lvl
    Task(
        "Mining highlvl",
        Skills(10, 0, 0),
        Skills(1, 0, 0),
        1, 100_000
    )
]

model = MultiPeriodAssignmentModel(24, accounts, task_db)
solv = model.get_solver()
print("Variables:", solv.NumVariables())
print("Constraints:", solv.NumConstraints())
solv.SetTimeLimit(600_000)
solv.EnableOutput()

start = time.perf_counter()
status = solv.Solve()
elapsed = time.perf_counter() - start

print(f"Solve time: {elapsed:.3f} seconds")
print(status)
print(status == Solver.OPTIMAL)

if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
    schedule = pd.DataFrame(
        "Idle",
        index=[account.name for account in model.workforce],
        columns=[f"Period {t + 1}" for t in range(model.periods)]
    )
    schedule.index.name = "Account"

    for (w, j, t), variable in model.task_assignments.items():
        if t < model.periods and variable.solution_value() > 0.5:
            schedule.iat[w, t] = model.tasks[j].name

    print(schedule.to_string())
else:
    print("No feasible solution to display.")
