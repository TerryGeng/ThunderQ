from thunderq.helper.iq_calibration_container import IQCalibrationContainer
from thunderq.driver.ASG import ASG
from thunderq.procedure import IQModulation


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
        self.after_drive_padding = 2e-6

    @property
    def drive_freq(self):
        return super().target_freq

    @drive_freq.setter
    def drive_freq(self, value):
        super().target_freq = value

    @property
    def after_drive_padding(self):
        return super().after_mod_padding

    @after_drive_padding.setter
    def after_drive_padding(self, value):
        super().after_mod_padding = value

    @property
    def drive_lo_freq(self):
        return super().lo_freq

    @drive_lo_freq.setter
    def drive_lo_freq(self, value):
        super().lo_freq = value

    @property
    def drive_lo_power(self):
        return super().lo_power

    @drive_lo_power.setter
    def drive_lo_power(self, value):
        super().lo_power = value

    @property
    def drive_len(self):
        return super().mod_len

    @drive_len.setter
    def drive_len(self, value):
        super().mod_len = value

    @property
    def drive_mod_amp(self):
        return super().mod_amp

    @drive_mod_amp.setter
    def drive_mod_amp(self, value):
        super().mod_amp = value

