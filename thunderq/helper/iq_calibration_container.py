import math

class IQCalibrationContainer:
    def __init__(self,
                 I_offset: float=0,
                 Q_offset: float=0,
                 I_amp_factor: float=1,
                 Q_amp_factor: float=1,
                 I_phase_shift: float=0,
                 Q_phase_shift: float=0,
                 I_time_offset: float=0,
                 Q_time_offset: float=0
                 ):
        self.I_offset = I_offset
        self.Q_offset = Q_offset
        self.I_amp_factor = I_amp_factor
        self.Q_amp_factor = Q_amp_factor
        self.I_phase_shift = I_phase_shift
        self.Q_phase_shift = Q_phase_shift
        self.I_time_offset = I_time_offset
        self.Q_time_offset = Q_time_offset

def txt_to_dict(filename):
    text = open(filename).readlines()
    _dict = {}
    for line in text:
        fields = line.split()
        _dict[fields[0]] = fields[1]

    return _dict

def read_IQ_calibrate_file(filename):
    _dict = txt_to_dict(filename)
    I_amp_factor = 1
    Q_amp_factor = math.sin(float(_dict['change_mod_power_angle'])) / math.cos(float(_dict['change_mod_power_angle']))  # This sin/cos trick doesn't make sense to me. See my thesis for more details.
    return IQCalibrationContainer(
        I_offset=float(_dict['chI_offset_volt']),
        Q_offset=float(_dict['chQ_offset_volt']),
        I_amp_factor=I_amp_factor,
        Q_amp_factor=Q_amp_factor,
        I_phase_shift=0,
        Q_phase_shift=float(_dict['Q_phase'])/1e9,
        I_time_offset=0,
        Q_time_offset=float(_dict['Q_time_offset'])/1e9  # If this term is < 1e-9, then it is meaningless, since it goes beyond sample rate
    )
