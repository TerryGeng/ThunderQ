import numpy as np
from thunderq.driver.ASG import ASG
from thunderq.helper import waveform as waveform
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.helper.sequence import Sequence
from .procedure import Procedure
import thunderq.runtime as runtime

class IQModDrive(Procedure):
    def __init__(self,
                 mod_slice_name: str,
                 mod_I_name: str,
                 mod_Q_name: str,
                 lo_dev: ASG,
                 mod_IQ_calibration: IQCalibrationContainer=None
                 ):
        super().__init__("Drive")
        self.mod_slice = mod_slice_name
        self.mod_I_name = mod_I_name
        self.mod_Q_name = mod_Q_name
        self.lo_dev = lo_dev

        if not mod_IQ_calibration:
            self.mod_IQ_calibration = IQCalibrationContainer()
        else:
            self.mod_IQ_calibration = mod_IQ_calibration


        self.lo_freq = mod_IQ_calibration.lo_freq # Hz, the suggested value of current calibration
        self.lo_power = mod_IQ_calibration.lo_power  # dBm, the suggested value of current calibration

        self.mod_freq = 50e6  # Hz, will be overridden given a probe frequency
        self.mod_amp = mod_IQ_calibration.mod_amp # V, the suggested value of current calibration

        # self.lo_freq = 5.747e9  # GHz
        # self.lo_power = 11  # dBm
        # self.drive_freq = 5.797e9 # GHz
        # self.mod_amp = 0.3  # V

        self.drive_len = 4096 * 1e-9  # The length of mod waveform, in sec.
        self.after_drive_padding = 1e-6  # Length of idle time after drive waveform, before probe signal.

    def set_drive_params(self, drive_freq=None, drive_len=None, drive_mod_amp=None, drive_lo_power=None):
        if drive_freq:
            self.drive_freq = drive_freq
        if drive_len:
            self.drive_len = drive_len
        if drive_mod_amp:
            self.drive_mod_amp = drive_mod_amp
        if drive_lo_power:
            self.lo_power = drive_lo_power

    def build_drive_waveform(self, drive_len, mod_freq, drive_mod_rel_amp, padding):
        dc_waveform = waveform.DC(drive_len, 1) * drive_mod_rel_amp

        IQ_waveform = waveform.CalibratedIQ(mod_freq,
                                            I_waveform=dc_waveform,
                                            IQ_cali=self.mod_IQ_calibration,
                                            down_conversion=False) # Use up conversion

        return waveform.Real(IQ_waveform).concat(waveform.Blank(padding)), \
               waveform.Imag(IQ_waveform).concat(waveform.Blank(padding))

    def pre_run(self, sequence: Sequence):
        if not self.drive_freq or not self.mod_amp:
            raise ValueError("Modulation parameters should be set first.")

        # Upper sideband is kept, in accordance with Orkesh's calibration
        self.mod_freq = self.drive_freq - self.lo_freq
        runtime.logger.info(f"MOD setup: LO freq {self.lo_freq/1e9} GHz, MOD freq {self.mod_freq/1e9} GHz, MOD amp {self.mod_amp} V.")
        self.lo_dev.set_frequency_amplitude(self.lo_freq, self.lo_power)
        self.lo_dev.run()

        I_waveform, Q_waveform = self.build_drive_waveform(self.drive_len, self.mod_freq, self.mod_amp, self.after_drive_padding)

        mod_slice: Sequence.Slice = sequence.slices[self.mod_slice]
        mod_slice.set_offset(self.mod_I_name, self.mod_IQ_calibration.I_offset)
        mod_slice.set_offset(self.mod_Q_name, self.mod_IQ_calibration.Q_offset)
        mod_slice.add_waveform(self.mod_I_name, I_waveform)
        mod_slice.add_waveform(self.mod_Q_name, Q_waveform)
        mod_slice.set_waveform_padding(self.mod_I_name, Sequence.PADDING_BEFORE)
        mod_slice.set_waveform_padding(self.mod_Q_name, Sequence.PADDING_BEFORE)

    def post_run(self):
        pass

