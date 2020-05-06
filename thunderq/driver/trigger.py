import thunderq.runtime as runtime

if not runtime.dry_run:
    import path_to_devices
    import DG645 # importing Orkesh's device interface
else:
    from .dummy import Dummy
    DG645 = Dummy("DG645")
    DG645.DEVICE = DG645.get_self

class TriggerDevice:
    def __init__(self):
        pass

    def set_cycle_frequency(self, frequency):
        raise NotImplementedError

    def set_trigger(self, trigger_line, start_from, duration):
        raise NotImplementedError

class TriggerDG645(TriggerDevice):
    def __init__(self):
        super().__init__()
        self.dev = DG645.DEVICE()
        self.dev.basic_setup()

    def set_cycle_frequency(self, frequency):
        self.dev.setup_FREQ(frequency)

    def set_trigger(self, trigger_line, start_from, duration):
        if trigger_line == "T0":
            self.dev.setup_T1(None, 2.5) # 2.5 is amplitude
        elif trigger_line == "AB":
            self.dev.setup_AB(start_from, duration, 2.5)
        elif trigger_line == "CD":
            self.dev.setup_CD(start_from, duration, 2.5)
        elif trigger_line == "EF":
            self.dev.setup_EF(start_from, duration, 2.5)
        elif trigger_line == "GH":
            self.dev.setup_GH(start_from, duration, 2.5)

