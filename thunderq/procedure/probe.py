import numpy as np
from thunderq.helper.sequence import Sequence
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.procedure import IQModulation

from device_repo import Digitizer, PSG


def get_amp_phase(freq, data, sample_rate=1e9):
    data_length = len(data)
    sin_sum = 0
    cos_sum = 0
    for t in range(data_length):
        cos_projection = np.cos(2 * np.pi * freq * t / sample_rate)
        sin_projection = np.sin(2 * np.pi * freq * t / sample_rate)
        sin_sum += data[t] * sin_projection
        cos_sum += data[t] * cos_projection

    sin_avg = 2 * sin_sum / data_length
    cos_avg = 2 * cos_sum / data_length

    amp = np.sqrt(sin_avg**2 + cos_avg**2)
    phase = np.arctan2(sin_avg, cos_avg)

    return amp, phase


class IQModProbe(IQModulation):
    def __init__(self,
                 *,
                 probe_mod_slice_name: str,
                 probe_mod_I_name: str,
                 probe_mod_Q_name: str,
                 probe_lo_dev: PSG,
                 acquisition_slice_name: str,
                 acquisition_dev: Digitizer,
                 mod_IQ_calibration: IQCalibrationContainer = None,
                 result_prefix=""
                 ):

        super().__init__(
            mod_slice_name=probe_mod_slice_name,
            mod_I_name=probe_mod_I_name,
            mod_Q_name=probe_mod_Q_name,
            lo_dev=probe_lo_dev,
            mod_IQ_calibration=mod_IQ_calibration,
            result_prefix=result_prefix
        )

        self.name = "IQ Modulated Probe"
        self.acquisition_slice_name = acquisition_slice_name
        self.acquisition_dev = acquisition_dev

        self.probe_len = 4096 * 1e-9 # The length of mod waveform, in sec.
        self.readout_len = 1024
        self.repeat = 200

        self.result_amp = None
        self.result_phase = None

    @property
    def probe_freq(self):
        return super().target_freq

    @probe_freq.setter
    def probe_freq(self, value):
        super().target_freq = value

    @property
    def probe_mod_amp(self):
        return super().mod_amp

    @probe_mod_amp.setter
    def probe_mod_amp(self, value):
        super().lo_power = value

    @property
    def probe_lo_power(self):
        return super().mod_amp

    @probe_lo_power.setter
    def probe_lo_power(self, value):
        super().lo_power = value

    def pre_run(self, sequence: Sequence):
        super().pre_run(sequence)

        self.acquisition_dev.set_sample_number(self.readout_len)
        self.acquisition_dev.set_repeats(self.repeat)
        self.acquisition_dev.set_trigger_delay(0)

    def post_run(self):
        self.acquisition_dev.start_acquire()
        ch_I_data, ch_Q_data = self.acquisition_dev.fetch_average()

        I_amp_avg, I_phase_avg = get_amp_phase(self.mod_freq, ch_I_data)
        Q_amp_avg, Q_phase_avg = get_amp_phase(self.mod_freq, ch_Q_data)

        self.result_amp = (I_amp_avg**2 + Q_amp_avg**2) / 2
        self.result_phase = (Q_amp_avg + np.pi/2 + I_amp_avg) / 2

        return {
            f"{self.result_prefix}amplitude": self.result_amp,
            f"{self.result_prefix}phase": self.result_phase
        }
