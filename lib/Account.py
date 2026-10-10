class Account:
    def __init__(self, mining, herblore, woodcutting):
        self.mining = mining
        self.herblore = herblore
        self.woodcutting = woodcutting

    def __str__(self):
        return f'{self.mining}, {self.herblore}, {self.woodcutting}'

