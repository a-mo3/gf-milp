from lib.Skills import Skills

class Account:
    def __init__(self, name, skills, startup_cost=13_0000):
        self.name = name
        self.skills = skills
        self.startup_cost=startup_cost

    def __init__(self, name):
        self.name = name
        self.skills = Skills(0, 0, 0)
        self.startup_cost=13_000_000

    def __str__(self):
        self.startup_cost=13_000_000
        self.skills = Skills(0, 0, 0)
        return f'{self.name} {self.skill}'
