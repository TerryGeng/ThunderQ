import thunderq.runtime as runtime

if not runtime.dry_run:
    import path_to_devices
    import E8257C
    import SGS993_MOD1
else:
    from .dummy import Dummy
    E8257C = Dummy("E8257C")
    E8257C.DEVICE = E8257C.get_self
    SGS993_MOD1 = Dummy("SGS993_MOD1")
    SGS993_MOD1.DEVICE = SGS993_MOD1.get_self


## Analog Signal Generator
class ASG:
    def __init__(self, name):
        self.name = name

    def run(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def set_frequency_amplitude(self, freq_in_hz, amp_in_db):
        raise NotImplementedError


class ASG_E8257C(ASG):
    def __init__(self):
        super().__init__("PSG E8257C")
        self.dev = E8257C.DEVICE()
        self.dev.basic_setup()
        self.dev.RFOFF()
        self.dev.setFreqAmp(5.0e9, 10) # safe default value
        runtime.logger.debug("E8257C: Initialized. RF set to OFF.")

    def run(self):
        runtime.logger.debug("E8257C: RF set to ON.")
        self.dev.RFON()

    def stop(self):
        runtime.logger.debug("E8257C: RF set to OFF.")
        self.dev.RFOFF()

    def set_frequency_amplitude(self, freq_in_hz, amp_in_db):
        runtime.logger.debug(f"E8257C: Params set: Freq={freq_in_hz}Hz, Amp={amp_in_db}dBm")
        self.dev.setFreqAmp(freq_in_hz, amp_in_db)


class ASG_SGS993(ASG):
    def __init__(self):
        super().__init__("SGS993")
        self.dev = SGS993_MOD1.DEVICE()
        self.dev.basic_setup()
        self.dev.RFOFF()
        self.dev.setFreqAmp(5.0e9, 10) # safe default value
        runtime.logger.debug("SGS993: Initialized. RF set to OFF.")

    def run(self):
        runtime.logger.debug("SGS993: RF set to ON.")
        self.dev.RFON()

    def stop(self):
        runtime.logger.debug("SGS993: RF set to OFF.")
        self.dev.RFOFF()

    def set_frequency_amplitude(self, freq_in_hz, amp_in_db):
        runtime.logger.debug(f"SGS993: Params set: Freq={freq_in_hz}Hz, Amp={amp_in_db}dBm")
        self.dev.setFreqAmp(freq_in_hz, amp_in_db)
