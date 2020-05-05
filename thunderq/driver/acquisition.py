import path_to_devices
import ATS9870


class AcquisitionDevice:
    def __init__(self, name):
        self.name = name

    def set_acquisition_params(self, length, repeats, delay_after_trigger):
        raise NotImplementedError

    def start_acquisition(self):
        raise NotImplementedError

    def fetch_data(self):
        raise NotImplementedError


class Acquisition_ATS9870(AcquisitionDevice):
    def __init__(self):
        super().__init__("ATS9870")
        self.dev = ATS9870.DEVICE()
        self.length = 1024
        self.repeats = 100
        self.delay = 0

    def set_acquisition_params(self, length, repeats, delay_after_trigger):
        self.length = length
        self.repeats = repeats
        self.delay = delay_after_trigger

    def start_acquisition(self):
        self.dev.req(self.delay, self.length, self.repeats) # This method is non-blocking

    def fetch_data(self):
        chA_data, chB_data = self.dev.get() # This method won't return until acquisition finishes.
        return chA_data, chB_data

    # TODO: calibration

