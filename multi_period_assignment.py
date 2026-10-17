# here we model starting with x base accounts, and given market constraints and a set of methods find optimal training path
# we do not consider any reward for training here other than levels
import time

import pandas as pd
from ortools.linear_solver import pywraplp
from ortools.linear_solver.pywraplp import Solver

from lib.Account import Account
from lib.Skills import Skills
from lib.Task import Task


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

        # objective function
        self.solver.Maximize(
            self.solver.Sum(
                task.reward * self.task_assignments[w, j, t]
                for w in range(len(self.workforce))
                for j, task in enumerate(self.tasks)
                for t in range(self.periods)
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
