import numpy as np
from thunderq.helper import waveform as waveform
from thunderq.helper.sequence import Sequence
from thunderq.driver.acqusition import AcquisitionDevice
from thunderq.driver.ASG import ASG
from thunderq.procedure import Procedure

class IQModProbe(Procedure):
    def __init__(self,
                 probe_mod_slice_name: str,
                 probe_mod_I_name: str,
                 probe_mod_Q_name: str,
                 probe_lo_slice_name: str,
                 probe_lo_dev: ASG,
                 acquisition_slice_name: str,
                 acquisition_dev: AcquisitionDevice
                 ):

        super().__init__("IQ Mod Probe")
        self.mod_slice = probe_mod_slice_name
        self.mod_I_name = probe_mod_I_name
        self.mod_Q_name = probe_mod_Q_name
        self.lo_slice = probe_lo_slice_name
        self.lo_dev = probe_lo_dev
        self.acquisition_slice_name = acquisition_slice_name
        self.acquisition_dev = acquisition_dev

        self.mod_IQ_calib_array = [[1, 0, 0], [1, 0, 0]]

        self.lo_power = -5  # dBm

        self.mod_freq = 50e6  # Hz
        self.mod_amp = 1 # V

        self.probe_len = 4096 * 1e-9 # The length of mod waveform, in sec.
        self.readout_len = 1024
        self.repeat = 200

        self.probe_freq = None
        self.probe_mod_amp = None

        self.result_amp = None
        self.result_phase = None

    def set_probe_params(self, probe_freq, probe_mod_amp, probe_lo_power):
        self.probe_freq = probe_freq
        self.mod_amp = probe_mod_amp
        self.lo_power = probe_lo_power

    def pre_run(self, sequence: Sequence):
        if not self.prob_freq or not self.mod_amp:
            raise ValueError("Probe parameters should be set first.")

        self.probe_lo_dev.set_frequency_amplitude(self.probe_freq - self.mod_freq, self.mod_amp)
        self.probe_lo_dev.run()

        I_waveform, Q_waveform = self._build_readout_waveform(self.prob_len, self.prob_mod_rel_amp)

        mod_slice: Sequence.Slice = sequence.slices[self.mod_slice]
        mod_slice.add_waveform(self.mod_I_name, I_waveform)
        mod_slice.add_waveform(self.mod_Q_name, Q_waveform)

        self.acquisition_dev.set_acquisition_params(length=self.readout_len,
                                                    repeats=self.repeat,
                                                    delay_after_trigger=0)
        self.acquisition_dev.start_acquisition()

    def post_run(self):
        ch_I_datas, ch_Q_datas = self.acquisition_dev.fetch_data()
        I_amp_sum, I_phase_sum = 0, 0
        Q_amp_sum, Q_phase_sum = 0, 0

        for ch_I_data in ch_I_datas:
            I_amp, I_phase = self.get_amp_phase(self.probe_mod_freq, ch_I_data)
            I_amp_sum += I_amp
            I_phase_sum += I_phase

        for ch_Q_data in ch_Q_datas:
            Q_amp, Q_phase = self.get_amp_phase(self.probe_mod_freq, ch_Q_data)
            Q_amp_sum += Q_amp
            Q_phase_sum += Q_phase

        I_amp_avg = I_amp_sum / self.repeats
        I_phase_avg = I_phase_sum / self.repeats
        Q_amp_avg = Q_amp_sum / self.repeats
        Q_phase_avg = Q_phase_sum / self.repeats # I_phase_avg should almost equal to Q_phase_avg

        self.result_amp = np.sqrt(I_amp_avg**2 + Q_amp_avg**2)
        self.result_phase = np.arctan2(Q_amp_avg, I_amp_avg)

    def last_result(self):
        return self.result_amp, self.result_phase

    def _build_readout_waveform(self, prob_len, prob_mod_rel_amp):
        dc_waveform = waveform.DC(prob_len, 1) * prob_mod_rel_amp

        # vIQmixer here is used just for calibrating IQ pulse
        # I_pulse = wave.vIQmixer.up_conversion(
        #     self.heterodyne_freq,
        #     I = self.mod_I_src.max_amplitude * dc_waveform,
        #     cali_array = self.mod_IQ_calib_array
        # )
        # Q_pulse = wave.vIQmixer.up_conversion(
        #     self.heterodyne_freq,
        #     Q = self.mod_Q_src.max_amplitude * dc_waveform,
        #     cali_array = self.mod_IQ_calib_array
        # )
        # TODO: Above part is actually not completely correct.

        IQ_waveform = waveform.CalibratedIQ(self.heterodyne_freq,
                                            I_waveform=dc_waveform,
                                            carry_cali_matrix=self.mod_IQ_calib_array)

        return waveform.Real(IQ_waveform), waveform.Imag(IQ_waveform)

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
