class Account:
    def __init__(self, name, mining, herblore, woodcutting):
        self.name = name
        self.mining = mining
        self.herblore = herblore
        self.woodcutting = woodcutting

    def __str__(self):
        return f'{self.name} {self.mining}, {self.herblore}, {self.woodcutting}'

