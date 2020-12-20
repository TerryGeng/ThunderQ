class Trigger:
    def __init__(self):
        pass

    def set_cycle_frequency(self, freq):
        raise NotImplementedError

    def set_channel_delay(self, channel, raise_at, drop_after):
        raise NotImplementedError


# device_repo DG support
class DGTrigger(Trigger):
    from device_repo import DG

    def __init__(self, trigger_dev: DG):
        super().__init__()
        self.device = trigger_dev

    def set_cycle_frequency(self, freq):
        self.device.set_cycle_frequency(freq)

    def set_channel_delay(self, channel, raise_at, drop_after):
        self.device.set_channel_delay(channel, raise_at, drop_after)
