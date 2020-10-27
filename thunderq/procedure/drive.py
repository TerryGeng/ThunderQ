import numpy as np
from thunderq.helper import waveform as waveform
from thunderq.helper.sequence import Sequence
from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.driver.ASG import ASG
from thunderq.procedure import IQModulation
import thunderq.runtime as runtime


class IQModDrive(IQModulation):
    def __init__(self,
                 drive_mod_slice_name: str,
                 drive_mod_I_name: str,
                 drive_mod_Q_name: str,
                 drive_lo_dev: ASG,
                 mod_IQ_calibration: IQCalibrationContainer = None
                 ):

        super().__init__(drive_mod_slice_name, drive_mod_I_name, drive_mod_Q_name, drive_lo_dev, mod_IQ_calibration)
        self.name = "IQ Modulated Drive"
        self.set_drive_params(after_drive_padding=2e-6)

    def set_drive_params(self,
                         drive_freq=None,
                         drive_len=None,
                         drive_mod_amp=None,
                         drive_lo_power=None,
                         drive_lo_freq=None,
                         after_drive_padding=None):
        super().set_mod_params(target_freq=drive_freq,
                               mod_len=drive_len,
                               mod_amp=drive_mod_amp,
                               lo_power=drive_lo_power,
                               lo_freq=drive_lo_freq,
                               after_mod_padding=after_drive_padding)

