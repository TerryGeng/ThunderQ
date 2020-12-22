from thunderq.sequencer import DGTrigger, AWGChannel, WaveformGate
from thunderq.runtime import Logger
from device_repo import DeviceType, AWG, DG, Digitizer


class MockAWG:
    def __init__(self, name):
        self.name = name
        self.sample_rate = 1e9
        self.offset = 0.0
        self.amplitude = 0.0

        self.raw_waveform = None
        self.raw_waveform_amp = 0

        self.running = False

    def get_type(self):
        return DeviceType.ArbitraryWaveformGenerator

    def get_sample_rate(self):
        return self.sample_rate

    def write_raw_waveform(self, raw_waveform, amplitude):
        self.raw_waveform = raw_waveform
        self.raw_waveform_amp = amplitude

    def set_offset(self, offset_voltage):
        self.offset = offset_voltage

    def get_offset(self):
        return self.offset

    def run(self):
        self.running = True

    def stop(self):
        self.running = False

    def set_amplitude(self, amp):
        self.amplitude = amp

    def get_amplitude(self):
        return self.amplitude

    def plot_waveform(self, logger: Logger):
        from matplotlib.figure import Figure
        fig = Figure(figsize=(8, 4))
        ax = fig.subplots(1, 1)
        ax.plot(self.raw_waveform)
        fig.set_tight_layout(True)
        logger.get_plot_sender(self.name, title=self.name).send(fig)


class MockDG:
    def __init__(self):
        self.cycle_freq = 0
        self.channel_delays = {}

    def get_type(self):
        return DeviceType.DelayGenerator

    def set_cycle_frequency(self, freq_in_hz):
        self.cycle_freq = freq_in_hz

    def get_cycle_frequency(self):
        return self.cycle_freq

    def set_channel_delay(self, channel_index, rising_at, fall_after):
        self.channel_delays[channel_index] = (rising_at, fall_after)

    def get_channel_delay(self, channel_index):
        return self.channel_delays[channel_index]


class MockDigitizer(Digitizer):
    def __init__(self):
        super().__init__(None)
        self.sample_rate = 1e9
        self.samples_per_record = 1024
        self.repeats = 512
        self.channel_ranges = {}
        self.trigger_level = 0
        self.trigger_delay = 0
        self.trigger_timeout = 0

    def get_type(self):
        return DeviceType.Digitizer

    def set_sample_number(self, number_of_samples):
        self.samples_per_record = number_of_samples

    def set_input_range(self, channel, _range):
        self.channel_ranges[channel] = _range

    def set_repeats(self, repeats):
        self.repeats = repeats

    def set_trigger_level(self, trigger_level):
        self.trigger_level = trigger_level

    def set_trigger_delay(self, delay):
        self.trigger_delay = delay

    def set_trigger_timeout(self, timeout):
        self.trigger_timeout = timeout

    def get_sample_rate(self):
        return self.sample_rate

    def get_sample_number(self):
        return self.samples_per_record

    def get_input_range(self, channel):
        return self.channel_ranges[channel]

    def get_repeats(self):
        assert self.repeats > 0
        return self.repeats

    def get_trigger_level(self):
        return self.trigger_level

    def get_trigger_delay(self):
        return self.trigger_delay

    def get_trigger_timeout(self):
        return self.trigger_timeout

    def acquire_and_fetch(self):
        return [
            [[1], [1]],
            [[0], [0]]
        ]

    def acquire_and_fetch_average(self):
        return [[1], [0]]

    def start_acquire(self):
        pass

    def fetch(self):
        return [
            [[1], [1]],
            [[0], [0]]
        ]

    def fetch_average(self):
        return [[1], [0]]


mock_awg0 = AWGChannel("mock_awg0", MockAWG("mock_awg0"))
mock_awg1 = AWGChannel("mock_awg1", MockAWG("mock_awg1"))
mock_awg2 = AWGChannel("mock_awg2", MockAWG("mock_awg2"))
mock_awg3 = AWGChannel("mock_awg3", MockAWG("mock_awg3"))
mock_awg4 = AWGChannel("mock_awg4", MockAWG("mock_awg4"))
mock_awg5 = AWGChannel("mock_awg5", MockAWG("mock_awg5"))
mock_awg6 = AWGChannel("mock_awg6", MockAWG("mock_awg6"))
mock_awg7 = AWGChannel("mock_awg7", MockAWG("mock_awg7"))
mock_awg8 = AWGChannel("mock_awg8", MockAWG("mock_awg8"))
mock_awg9 = AWGChannel("mock_awg9", MockAWG("mock_awg9"))

mock_awg10_gate = WaveformGate("mock_awg10_gate")
mock_awg11_gate = WaveformGate("mock_awg11_gate")
mock_awg12_gate = WaveformGate("mock_awg12_gate")

mock_awg10 = AWGChannel("mock_awg10", MockAWG("mock_awg10"), mock_awg10_gate)
mock_awg11 = AWGChannel("mock_awg11", MockAWG("mock_awg11"), mock_awg11_gate)
mock_awg12 = AWGChannel("mock_awg12", MockAWG("mock_awg12"), mock_awg12_gate)
mock_dg = DGTrigger(MockDG())
mock_digitizer = MockDigitizer()
