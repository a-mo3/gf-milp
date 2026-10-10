class ObjectiveTask:
    def __init__(self, name, mining_req, herb_req, woodcutting_req, reward, max_allowed):
        self.name = name
        self.mining_req = mining_req
        self.herb_req = herb_req
        self.woodcutting_req = woodcutting_req
        self.reward = reward
        self.max_allowed = max_allowed

    def can_assign(self, account):
        return (
                account.mining >= self.mining_req
                and account.herblore >= self.herb_req
                and account.woodcutting >= self.woodcutting_req
        )
