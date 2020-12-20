from thunderq.waveforms.native import Waveform


class WaveformChannel:
    def __init__(self, name, gated_by=None):
        self.name = name
        if gated_by:
            assert isinstance(gated_by, WaveformGate)
            self.gate_by = gated_by
            self.gate_by.base = self
        else:
            self.gate_by = None
        self.waveform = None

    def get_gated_waveform(self) -> Waveform:
        if self.gate_by:
            assert isinstance(self.gate_by, WaveformChannel)
            gate = self.gate_by.get_gated_waveform()
            if gate:
                return self.gate_by.get_gated_waveform() * self.waveform
            else:
                return self.waveform
        else:
            return self.waveform

    def set_waveform(self, waveform: Waveform):
        self.waveform = waveform

    def run(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def set_offset(self, offset):
        raise NotImplementedError

    def get_offset(self):
        raise NotImplementedError


class WaveformGate(WaveformChannel):
    def __init__(self, name):
        super().__init__(name)
        self.name = name
        self.base = None

    def run(self):
        pass

    def stop(self):
        pass

    def set_offset(self, offset):
        raise NotImplementedError

    def get_offset(self):
        return 0


# device_repo AWG support
class AWGChannel(WaveformChannel):
    from device_repo import AWG

    def __init__(self, name, channel_dev: AWG, gate_by: WaveformGate = None):
        # channel_dev: AWG channel from device_repo

        super().__init__(name, gate_by)
        self.name = name
        self.device = channel_dev

    def run(self):
        waveform = self.get_gated_waveform()
        wave_data, amplitude = waveform.normalized_sample(
            self.device.get_sample_rate())

        self.device.write_raw_waveform(wave_data, amplitude)

        self.device.run()

    def stop(self):
        self.device.stop()

    def get_offset(self):
        return self.device.get_offset()

    def set_offset(self, offset):
        self.device.set_offset(offset)

