import numpy as np
from thunderq.helper import waveform as waveform
from thunderq.helper.sequence import Sequence
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.driver.acqusition import AcquisitionDevice
from thunderq.driver.ASG import ASG
from thunderq.procedure import Procedure
import thunderq.runtime as runtime

class IQModProbe(Procedure):
    def __init__(self,
                 probe_mod_slice_name: str,
                 probe_mod_I_name: str,
                 probe_mod_Q_name: str,
                 probe_lo_dev: ASG,
                 acquisition_slice_name: str,
                 acquisition_dev: AcquisitionDevice,
                 mod_IQ_calibration: IQCalibrationContainer = None
                 ):

        super().__init__("IQ Mod Probe")
        self.mod_slice = probe_mod_slice_name
        self.mod_I_name = probe_mod_I_name
        self.mod_Q_name = probe_mod_Q_name
        self.lo_dev = probe_lo_dev
        self.acquisition_slice_name = acquisition_slice_name
        self.acquisition_dev = acquisition_dev

        if not mod_IQ_calibration:
            self.mod_IQ_calibration = IQCalibrationContainer()
        else:
            self.mod_IQ_calibration = mod_IQ_calibration

        self.lo_freq = mod_IQ_calibration.lo_freq # Hz, the suggested value of current calibration
        self.lo_power = mod_IQ_calibration.lo_power  # dBm, the suggested value of current calibration

        #self.mod_freq = 50e6  # Hz
        self.mod_amp = mod_IQ_calibration.mod_amp # V, the suggested value of current calibration

        self.probe_len = 4096 * 1e-9 # The length of mod waveform, in sec.
        self.readout_len = 1024
        self.repeat = 200

        self.probe_freq = None
        self.probe_mod_amp = None

        self.result_amp = None
        self.result_phase = None

    def set_probe_params(self, probe_freq, probe_mod_amp=None, probe_lo_power=None):
        self.probe_freq = probe_freq
        if probe_mod_amp is not None:
            self.mod_amp = probe_mod_amp
        if probe_lo_power is not None:
            self.lo_power = probe_lo_power

    def pre_run(self, sequence: Sequence):
        if not self.probe_freq or not self.mod_amp:
            raise ValueError("Probe parameters should be set first.")

        # Upper sideband is kept, in accordance with Orkesh's calibration
        mod_freq = self.probe_freq - self.lo_freq
        runtime.logger.info(f"Probe setup: LO freq {self.lo_freq/1e9} GHz, MOD freq {mod_freq/1e9} GHz.")
        self.lo_dev.set_frequency_amplitude(self.lo_freq, self.lo_power)
        self.lo_dev.run()

        I_waveform, Q_waveform = self.build_readout_waveform(self.probe_len, self.mod_freq, self.mod_amp)

        mod_slice: Sequence.Slice = sequence.slices[self.mod_slice]
        mod_slice.set_offset(self.mod_I_name, self.mod_IQ_calibration.I_offset)
        mod_slice.set_offset(self.mod_Q_name, self.mod_IQ_calibration.Q_offset)
        mod_slice.add_waveform(self.mod_I_name, I_waveform)
        mod_slice.add_waveform(self.mod_Q_name, Q_waveform)
        mod_slice.set_waveform_padding(self.mod_I_name, Sequence.PADDING_BEFORE)
        mod_slice.set_waveform_padding(self.mod_Q_name, Sequence.PADDING_BEFORE)

        self.acquisition_dev.set_acquisition_params(length=self.readout_len,
                                                    repeats=self.repeat,
                                                    delay_after_trigger=0)
        self.acquisition_dev.start_acquisition()

    def post_run(self):
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

        self.result_amp = np.sqrt(I_amp_avg**2 + Q_amp_avg**2)
        self.result_phase = np.arctan2(Q_amp_avg, I_amp_avg)

    def last_result(self):
        return self.result_amp, self.result_phase

    def build_readout_waveform(self, prob_len, mod_freq, prob_mod_rel_amp):
        dc_waveform = waveform.DC(prob_len, 1) * prob_mod_rel_amp

        IQ_waveform = waveform.CalibratedIQ(mod_freq,
                                            I_waveform=dc_waveform,
                                            IQ_cali=self.mod_IQ_calibration,
                                            down_conversion=False) # Use up conversion

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
