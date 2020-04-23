import path_to_devices
import E8257C
import SGS993

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

    def run(self):
        self.dev.RFON()

    def stop(self):
        self.dev.RFOFF()

    def set_frequency_amplitude(self, freq_in_hz, amp_in_db):
        self.dev.setFreqAmp(freq_in_hz, amp_in_db)


class ASG_SGS993(ASG):
    def __init__(self):
        super().__init__("SGS993")
        self.dev = SGS993.DEVICE()
        self.dev.basic_setup()
        self.dev.RFOFF()
        self.dev.setFreqAmp(5.0e9, 10) # safe default value

    def run(self):
        self.dev.RFON()

    def stop(self):
        self.dev.RFOFF()

    def set_frequency_amplitude(self, freq_in_hz, amp_in_db):
        self.dev.setFreqAmp(freq_in_hz, amp_in_db)
