from lib.Skills import Skills

class Account:
    def __init__(self, name, skills):
        self.name = name
        self.skills = skills

    def __init__(self, name):
        self.name = name
        self.skills = Skills(0, 0, 0)

    def __str__(self):
        return f'{self.name} {self.skill}'
