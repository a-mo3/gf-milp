from lib.Skills import Skills


# General task rather than objective task distinction i was making in the simple assignment
class Task:
    def __init__(self, name, skill_requirements, skill_rewards, max_accounts, production, consumption, required_team_size=0):
        if not isinstance(skill_requirements, Skills):
            raise TypeError("Provided skill requirements is not of type Skills")
        if not isinstance(skill_rewards, Skills):
            raise TypeError("Provided skill rewards is not of type Skills")

        self.name = name

        self.skill_requirements = skill_requirements

        # experience gained
        self.skill_rewards = skill_rewards


        self.max_accounts = max_accounts
        # for team bosses that require X teammates, huey, soulwars, mole(special technique)
        self.required_team_size = required_team_size

        self.production = production
        self.consumption = consumption

    def __str__(self):
        return self.name