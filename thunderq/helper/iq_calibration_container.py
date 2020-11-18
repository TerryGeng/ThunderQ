import math

class IQCalibrationContainer:
    def __init__(self,
                 lo_freq: float=0,
                 lo_power: float=0,
                 mod_amp: float=0,
                 I_offset: float=0,
                 Q_offset: float=0,
                 I_amp_factor: float=1,
                 Q_amp_factor: float=1,
                 I_phase_shift: float=0,
                 Q_phase_shift: float=0,
                 I_time_offset: float=0,
                 Q_time_offset: float=0
                 ):
        self.lo_freq = lo_freq
        self.lo_power = lo_power
        self.mod_amp = mod_amp
        self.I_offset = I_offset
        self.Q_offset = Q_offset
        self.I_amp_factor = I_amp_factor
        self.Q_amp_factor = Q_amp_factor
        self.I_phase_shift = I_phase_shift
        self.Q_phase_shift = Q_phase_shift
        self.I_time_offset = I_time_offset
        self.Q_time_offset = Q_time_offset
