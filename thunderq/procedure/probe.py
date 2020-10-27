import numpy as np
from thunderq.helper import waveform as waveform
from thunderq.helper.sequence import Sequence
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.driver.acquisition import AcquisitionDevice
from thunderq.driver.ASG import ASG
from thunderq.procedure import IQModulation
import thunderq.runtime as runtime


class IQModProbe(IQModulation):
    def __init__(self,
                 probe_mod_slice_name: str,
                 probe_mod_I_name: str,
                 probe_mod_Q_name: str,
                 probe_lo_dev: ASG,
                 acquisition_slice_name: str,
                 acquisition_dev: AcquisitionDevice,
                 mod_IQ_calibration: IQCalibrationContainer = None
                 ):

        super().__init__(probe_mod_slice_name, probe_mod_I_name, probe_mod_Q_name, probe_lo_dev, mod_IQ_calibration)
        self.name = "IQ Modulated Probe"
        self.acquisition_slice_name = acquisition_slice_name
        self.acquisition_dev = acquisition_dev

        self.probe_len = 4096 * 1e-9 # The length of mod waveform, in sec.
        self.readout_len = 1024
        self.repeat = 200

        self.result_amp = None
        self.result_phase = None

    def set_probe_params(self, probe_freq, probe_mod_amp=None, probe_lo_power=None):
        super().set_mod_params(probe_freq, self.probe_len, probe_mod_amp, probe_lo_power)

    def pre_run(self, sequence: Sequence):
        super().pre_run(sequence)

        self.acquisition_dev.set_acquisition_params(length=self.readout_len,
                                                    repeats=self.repeat,
                                                    delay_after_trigger=0)

    def post_run(self):
        self.acquisition_dev.start_acquisition()
        ch_I_datas, ch_Q_datas = self.acquisition_dev.fetch_data()
        I_amp_sum, I_phase_sum = 0, 0
        Q_amp_sum, Q_phase_sum = 0, 0

        for ch_I_data in ch_I_datas:
            I_amp, I_phase = self.get_amp_phase(self.mod_freq, ch_I_data)
            I_amp_sum += I_amp
            I_phase_sum += I_phase

        for ch_Q_data in ch_Q_datas:
            Q_amp, Q_phase = self.get_amp_phase(self.mod_freq, ch_Q_data)
            Q_amp_sum += Q_amp
            Q_phase_sum += Q_phase

        I_amp_avg = I_amp_sum / self.repeat
        I_phase_avg = I_phase_sum / self.repeat
        Q_amp_avg = Q_amp_sum / self.repeat
        Q_phase_avg = Q_phase_sum / self.repeat # I_phase_avg should almost equal to Q_phase_avg

        # self.result_amp = np.sqrt(I_amp_avg**2 + Q_amp_avg**2)
        # self.result_phase = np.arctan2(Q_amp_avg, I_amp_avg)
        self.result_amp = (I_amp_avg**2 + Q_amp_avg**2) / 2
        self.result_phase = (Q_amp_avg + np.pi/2 + I_amp_avg) / 2

    def last_result(self):
        return self.result_amp, self.result_phase

    def get_amp_phase(self, freq, data, sample_rate=1e9):
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
