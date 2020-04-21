## Analog Signal Generator
class ASGChannel:
    def __init__(self, _name, _rc):
        self.rc = _rc
        self.name = _name

    def set_frequency(self, freq):
        self.rc.setValue('Frequency', freq)

    def set_power(self, power_in_db):
        self.rc.setValue('Power', power_in_db)
