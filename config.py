# TODO Config is a misleading name, maybe change to something like values
class Config:
    def __init__(self):
        self.min_val = self.min_sat = self.min_hue = 0
        self.max_val = self.max_sat = 255
        self.max_hue = 360