import thunderq.runtime as runtime

if not runtime.dry_run:
    import path_to_devices
    import ATS9870
else:
    from .dummy import Dummy
    ATS9870 = Dummy("ATS9870")
    ATS9870.DEVICE = ATS9870.get_self
    ATS9870.get = lambda : [0], [0]

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
        runtime.logger.debug("ATS9870: Initialized.")

    def set_acquisition_params(self, length, repeats, delay_after_trigger):
        self.length = length
        self.repeats = repeats
        self.delay = delay_after_trigger

    def start_acquisition(self):
        runtime.logger.debug("ATS9870: Acquisition requested.")
        runtime.logger.debug(f"ATS9870: With params: length={self.length}, delay={self.delay}, repeats={self.repeats}")
        self.dev.req(self.delay, self.length, self.repeats) # This method is non-blocking

    def fetch_data(self):
        runtime.logger.debug("ATS9870: Fetching data.")
        chA_data, chB_data = self.dev.get() # This method won't return until acquisition finishes.
        return chA_data, chB_data

    # TODO: calibration

