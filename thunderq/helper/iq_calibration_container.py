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

def txt_to_dict(filename):
    text = open(filename).readlines()
    _dict = {}
    for line in text:
        fields = line.split()
        _dict[fields[0]] = fields[1]

    return _dict

# TODO: this file changes too quickly. Please reconfirm its content every time.
def read_IQ_calibrate_file(filename):
    _dict = txt_to_dict(filename)

    lo_freq = float(_dict['src_power_freq']) * 1e9 # TODO: this is a typo, check and see if it is fixed the next time.
    Q_time_offset = float(_dict['Q_time_offset'])/1e9
    Q_phase = 2*math.pi*(-0.005e9) * Q_time_offset +  float(_dict['Q_phase']) # TODO: ?????? Ask Orkesh

    I_amp_factor = math.sin(float(_dict['change_mod_power_angle']))
    Q_amp_factor = math.cos(float(_dict['change_mod_power_angle']))
    # This sin/cos trick doesn't make too much sense to me. See  the calculations in my thesis for more details.

    return IQCalibrationContainer(
        lo_power=float(_dict['src_power_dBM']),
        lo_freq=lo_freq,
        mod_amp=float(_dict['change_mod_power']),
        I_offset=float(_dict['chI_offset_volt']),
        Q_offset=float(_dict['chQ_offset_volt']),
        I_amp_factor=I_amp_factor,
        Q_amp_factor=Q_amp_factor,
        I_phase_shift=0,
        Q_phase_shift=Q_phase,
        I_time_offset=0,
        Q_time_offset=Q_time_offset  # If this term is < 1e-9, then it is meaningless, since it goes beyond sample rate
    )
