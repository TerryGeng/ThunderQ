class WaveformChannel:
    def __init__(self, name):
        self.name = name

    def write_waveform(self, waveform):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def set_offset(self, offset):
        raise NotImplementedError

    def get_offset(self):
        raise NotImplementedError


# device_repo AWG support
class AWGChannel(WaveformChannel):
    from device_repo import AWG

    def __init__(self, name, channel_dev: AWG):
        # channel_dev: AWG channel from device_repo

        super().__init__(name)
        self.name = name
        self.device = channel_dev

    def write_waveform(self, waveform):
        wave_data, amplitude = waveform.normalized_sample(
            self.device.get_sample_rate())

        self.device.write_raw_waveform(wave_data, amplitude)

    def run(self):
        self.device.run()

    def stop(self):
        self.device.stop()

    def get_offset(self):
        return self.device.get_offset()

    def set_offset(self, offset):
        self.device.set_offset(offset)

