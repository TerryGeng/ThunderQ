import numpy as np
from thunderq.driver.AWG import AWGChannel
from thunderq.driver.ASG import ASG
from thunderq.helper import waveform as waveform
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.helper.sequence import Sequence
from .procedure import Procedure

class IQModDrive(Procedure):
    def __init__(self,
                 drive_mod_slice_name: str,
                 drive_mod_I_name: str,
                 drive_mod_Q_name: str,
                 drive_lo_dev: ASG,
                 mod_IQ_calibration: IQCalibrationContainer=None
                 ):
        super().__init__("Drive")
        self.drive_slice = drive_mod_slice_name
        self.mod_I_name = drive_mod_I_name
        self.mod_Q_name = drive_mod_Q_name
        self.lo_dev = drive_lo_dev

        if not mod_IQ_calibration:
            self.mod_IQ_calibration = IQCalibrationContainer()
        else:
            self.mod_IQ_calibration = mod_IQ_calibration

        self.drive_freq = 5.797e9  # GHz
        self.lo_power = 11  # dBm
        self.mod_freq = 50e6  # Hz
        self.mod_amp = 0.2  # V

        self.drive_len = 4096 * 1e-9  # The length of mod waveform, in sec.
        self.after_drive_padding = 1e-6  # Length of idle time after drive waveform, before probe signal.

    def set_drive_params(self, drive_freq, drive_len, drive_mod_amp):
        self.drive_freq = drive_freq
        self.drive_len = drive_len
        self.drive_mod_amp = drive_mod_amp

    def build_drive_waveform(self, drive_len, drive_mod_rel_amp):
        dc_waveform = waveform.DC(drive_len, 1) * drive_mod_rel_amp

        IQ_waveform = waveform.CalibratedIQ(self.mod_freq,
                                            I_waveform=dc_waveform,
                                            IQ_cali=self.mod_IQ_calibration)

        return waveform.Real(IQ_waveform).concat(waveform.Blank(self.after_drive_padding)), \
               waveform.Imag(IQ_waveform).concat(waveform.Blank(self.after_drive_padding))

    def pre_run(self, sequence: Sequence):
        if not self.drive_len or not self.drive_mod_amp:
            raise ValueError("Drive parameters should be set first.")

        # Lower sideband is kept, see IQ section of my thesis.
        self.lo_dev.set_frequency_amplitude(self.drive_len + self.mod_freq, self.mod_amp)
        self.lo_dev.run()

        I_waveform, Q_waveform = self.build_drive_waveform(self.drive_len, self.mod_amp)

        drive_slice: Sequence.Slice = sequence.slices[ self.drive_slice ]
        drive_slice.set_offset(self.mod_I_name, self.mod_IQ_calibration.I_offset)
        drive_slice.set_offset(self.mod_Q_name, self.mod_IQ_calibration.Q_offset)
        drive_slice.add_waveform(self.mod_I_name, I_waveform)
        drive_slice.add_waveform(self.mod_Q_name, Q_waveform)
        drive_slice.set_waveform_padding(self.mod_I_name, Sequence.PADDING_BEFORE)
        drive_slice.set_waveform_padding(self.mod_Q_name, Sequence.PADDING_BEFORE)

    def post_run(self):
        pass
