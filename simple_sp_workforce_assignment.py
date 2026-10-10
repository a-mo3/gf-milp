from ortools.linear_solver import pywraplp

from lib.Account import Account
from lib.ObjectiveTask import ObjectiveTask

# simple single period assignment

workforce = []

for i in range(10):
    workforce.append(Account(50, 1, 1))
for i in range(25):
    workforce.append(Account(1, 60, 1))
for i in range(5):
    workforce.append(Account(1, 1, 20))

objective_tasks = [
    ObjectiveTask("ProfitMine", 30, 0, 0, 100, 5),
    ObjectiveTask("ProfitHerb", 0, 50, 0, 1009, 29),
    ObjectiveTask("ProfitChop", 0, 0, 20, 10, 500)
]

solver = pywraplp.Solver.CreateSolver('SCIP')
if not solver:
    print('Solver not available')
    exit(0)

assigned_ints = {}

# No period assignment
# set bounds for ints, task eligibility

for worker_index, account in enumerate(workforce):
    for task_index, task in enumerate(objective_tasks):
        assigned_ints[worker_index, task_index] = solver.IntVar(
            0,
            int(task.can_assign(account)),
            f"assigned_task_{worker_index}_{task_index}"
        )

# workers have at most 1 task
for worker_index, account in enumerate(workforce):
    solver.Add(
        solver.Sum(
            assigned_ints[worker_index, j] for j in range(len(objective_tasks))
        ) <= 1
    )

# no more workers assigned to a task than its market limits
for j, task in enumerate(objective_tasks):
    solver.Add(
        solver.Sum(
            assigned_ints[worker_index, j] for worker_index in range(len(workforce))
        ) <= task.max_allowed
    )

# objective
solver.Maximize(
    solver.Sum(
        task.reward * assigned_ints[w, j]
        for w in range(len(workforce))
        for j, task in enumerate(objective_tasks)
    )
)

status = solver.Solve()

for (w,j), var in assigned_ints.items():
    print(f"{w} - {j}, {var.solution_value()}")

print(f"Was optimal {pywraplp.Solver.OPTIMAL == status}")