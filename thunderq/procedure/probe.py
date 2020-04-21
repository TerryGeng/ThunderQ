import numpy as np
from ..driver.AWG import AWGChannel
from ..helper import waveform as waveform
from .procedure import Procedure

class DoubleChannelProbe(Procedure):
    def __init__(self, prob_src, lo_src, mod_I_src: AWGChannel, mod_Q_src: AWGChannel, ATS):
        super().__init__("Double Channel Probe")
        self.prob_src = prob_src  # ASG Channel, continuous wave
        self.lo_src = lo_src  # ASG Channel, continuous wave, used in single channel readout
        self.mod_I_src = mod_I_src  # AWG Channel, M3202A
        self.mod_Q_src = mod_Q_src  # AWG Channel, M3202A
        self.mod_IQ_calib_array = [[1, 0, 0], [1, 0, 0]]

        self.ATS = ATS
        self.ATS_calib_array = [1, 1, np.pi / 2]

        self.ASG_power = -5  # in dBm

        self.heterodyne_freq = 50e6  # Hz
        self.prob_len = 10e-6
        self.readout_len = 1024
        self.repeat = 1000

        self.prob_freq = None
        self.prob_mod_rel_amp = None

        self.data = None

    def set_probe_params(self, prob_freq, prob_mod_rel_amp):
        self.prob_freq = prob_freq
        self.prob_mod_rel_amp = prob_mod_rel_amp

    def pre_run(self):
        if not self.prob_freq or not self.prob_mod_rel_amp:
            raise ValueError("Probe parameters should be set first.")

        # Set initial ASG amp
        self.set_ASG_power(self.ASG_power)

        self.mod_I_src.set_trigger_mode('External')
        self.mod_Q_src.set_trigger_mode('External')

        self.prob_src.set_frequency(self.prob_freq + self.heterodyne_freq)

        I_raw, Q_raw = self._build_readout_waveform(self.prob_len, self.prob_mod_rel_amp)

        self.mod_I_src.run_waveform(I_raw)
        self.mod_Q_src.run_waveform(Q_raw) # Cancel image by using IQ signal together. Work as a IR mixer.

    def post_run(self):
        self.data = self.ATS_Sp21_double_ch_readout()

    def data(self):
        return self.data

    def set_ASG_power(self, power_in_db):
        self.prob_src.set_power(power_in_db)
        self.prob_src_amp = power_in_db

    def set_heterodyne_freq(self, heterodyne_freq = 50e6):
        self.heterodyne_freq = heterodyne_freq

    def _build_readout_waveform(self, prob_len, prob_mod_rel_amp):
        dc_waveform = prob_mod_rel_amp * waveform.DC(prob_len, 1)

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

        IQ_raw = IQ_waveform.sample(self.mod_I_src.sample_rate).data

        return IQ_raw.real, IQ_raw.imag # TODO: CHECK DIFFERENCE BETWEEN OLD AND NEW CODE.

    # TODO: make this into driver
    def ATS_Sp21_double_ch_readout(self, readout_len=0, repeat=0, readout_freq=None):
        if readout_len == 0:
            readout_len = self.readout_len
        if repeat == 0:
            repeat = self.repeat
        if readout_freq is None:
            readout_freq = self.heterodyne_freq

        ch_I, ch_Q = self.ATS.getFFT(readout_len, 0, repeat, [ readout_freq ])

        a, b, phi = self.ATS_calib_array
        phase_factor = np.exp(1j * phi)

        # discard the phase returned by FFT, since we use I and Q to determine the phase
        ch_I_amp, ch_Q_amp = np.abs(ch_I[:, 0]), np.abs(ch_Q[:, 0])

        component = a * ch_I_amp + b * ch_Q_amp * phase_factor * 1j

        return np.average(component)


class SignalChannelProbe: # TODO: (Procedure)
    def __init__(self, prob_src, lo_src, mod_I_src: AWGChannel, mod_Q_src: AWGChannel, ATS):
        super().__init__("Single Channel Probe")
        self.prob_src = prob_src  # ASG Channel, continuous wave
        self.lo_src = lo_src  # ASG Channel, continuous wave, used in single channel readout
        self.mod_I_src = mod_I_src  # AWG Channel, M3202A
        self.mod_Q_src = mod_Q_src  # AWG Channel, M3202A
        self.mod_IQ_calib_array = [[1, 0, 0], [1, 0, 0]]

        self.ATS = ATS
        self.ATS_calib_array = [1, 1, np.pi / 2]

        self.prob_src_amp = -5  # in dBm

        self.heterodyne_freq = 50e6  # Hz
        self.prob_len = 10e-6
        self.readout_len = 1024
        self.repeat = 1000

        # Set initial ASG amp
        self.set_prob_src_amp(self.prob_src_amp) # TODO: [review] what is the right amp?

        self.mod_I_src.set_trigger_mode('External')
        self.mod_Q_src.set_trigger_mode('External')

    def set_prob_src_amp(self, prob_src_amp):
        self.prob_src.rc.setValue("Power", prob_src_amp)
        self.prob_src_amp = prob_src_amp

    def set_heterodyne_freq(self, heterodyne_freq = 50e6):
        self.heterodyne_freq = heterodyne_freq

    def _build_readout_waveform(self, prob_len, prob_mod_rel_amp):
        dc_waveform = prob_mod_rel_amp * waveform.DC(prob_len, 1)

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

        IQ_raw = IQ_waveform.sample(self.mod_I_src.sample_rate)

        return IQ_raw.real, IQ_raw.imag # TODO: CHECK DIFFERENCE BETWEEN OLD AND NEW CODE.

    def probe(self, prob_freq, prob_mod_rel_amp, prob_len=0):
        # prob_mod_rel_amp: relative amplitude, a factor from 0 to 1
        self.prob_src.set_frequency(prob_freq)
        self.lo_src.rc.set_frequency(prob_freq + self.heterodyne_freq)

        return self.ATS_Sp21_single_ch_readout()


    # TODO: make this into driver
    def ATS_Sp21_single_ch_readout(self, readout_len=0, repeat=0, readout_freq=None):
        if readout_len == 0:
            readout_len = self.readout_len
        if repeat == 0:
            repeat = self.repeat
        if readout_freq is None:
            readout_freq = self.readout_freq

        ch1, ch2 = self.ATS.getFFT(readout_len, 0, repeat, [ readout_freq ])

        a, b, phi = self.ATS_calib_array

        ch1_amp = ch1[:, 0]  # get 0-th column from ch1
        component = a * ch1_amp

        return np.average(component)
