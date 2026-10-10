from lib.Skills import Skills


# General task rather than objective task distinction i was making in the simple assignment
class Task:
    def __init__(self, name, skill_requirements, skill_rewards, reward, max_accounts):
        if not isinstance(skill_requirements, Skills):
            raise TypeError("Provided skill requirements is not of type Skills")
        if not isinstance(skill_rewards, Skills):
            raise TypeError("Provided skill rewards is not of type Skills")

        self.name = name

        self.skill_requirements = skill_requirements

        # experience gained
        self.skill_rewards = skill_rewards

        # actual reward contribution, analogous to gp
        self.reward = reward

        self.max_accounts = max_accounts