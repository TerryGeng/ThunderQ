# helper.waveforms
# -------------------------
# Data structure for waveforms.
# Note:
# 1. Everything stored in these Waveform class should be its functional form (loss-less form),
#     not raw waveforms data array.
# 2. Waveform can be converted to raw data array by using .sample(sample_rate) method.
# 3. Some operators like "*" have been overloaded, under the premise that doing so won't cause
#     unnecessary confusion. Therefore, I avoided overloading "+", "-" for this reason.
#

from textwrap import indent
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
import math


class Waveform:
    def __init__(self, width, amplitude):
        self.width = width
        self.amplitude = amplitude

    def at(self, time):
        raise NotImplementedError

    def direct_sample(self, sample_rate, min_unit=16):
        sample_points = np.arange(0, self.width, 1.0 / sample_rate)
        padding = []
        if len(sample_points) % min_unit != 0:
            padding_len = min_unit - (len(sample_points) % min_unit)
            padding = [0] * padding_len
        data = self.at(sample_points)
        data = np.concatenate([data, padding])
        return data

    def normalized_sample(self, sample_rate, min_unit=1):
        sample_points = np.arange(0, self.width, 1.0 / sample_rate)
        padding = []
        if len(sample_points) % min_unit != 0:
            padding_len = min_unit - (len(sample_points) % min_unit)
            padding = [0] * padding_len
        data = self.at(sample_points)
        data = np.concatenate([data, padding])
        max_abs = max(abs(data.max()), abs(data.min()))
        if max_abs != 0:
            data = data / max_abs  # Normalize

        return data, max_abs

    def thumbnail_sample(self, sample_points):
        # Used for generating sequence plot
        return self.at(sample_points)

    def plot(self, sample_rate):
        sample_points = np.arange(0, self.width, 1.0 / sample_rate)
        samples = self.direct_sample(sample_rate)
        plt.plot(sample_points, samples)
        plt.show()

    def concat(self, waveform):
        return Sequence(self, waveform)

    def append_to(self, waveform):
        return Sequence(waveform, self)

    def __pos__(self):
        return self

    def __neg__(self):
        cop = deepcopy(self)
        cop.amplitude = cop.amplitude * (-1)
        return cop

    def __add__(self, other):
        if isinstance(other, Waveform):
            return SumWave(self, other)
        else:
            # return SumWave(self,DC(self.width, other, 0))
            return self  # do nothing when encountering the case: (wave+other), like(DC(1,1)+1).

    def __abs__(self):
        cop = deepcopy(self)
        cop.amplitude = abs(cop.amplitude)
        return cop

    def __mul__(self, other):
        if isinstance(other, Waveform):
            return CarryWave(self, other)
        else:
            cop = deepcopy(self)
            cop.amplitude = cop.amplitude * other
        return cop

    def __str__(self):
        return f"<Waveform Base Object>"


class SumWave(Waveform):
    def __init__(self, wave1: Waveform, wave2: Waveform):
        super().__init__(max(wave1.width, wave2.width), 1)
        self.wave1 = wave1
        self.wave2 = wave2

    def at(self, time):
        return np.where(time > self.width, 0, (self.wave1.at(time) + self.wave2.at(time)) * self.amplitude)
        # The default value of self.amplitue is 1. In case of (wave1+wave2)*other, it will be set as other.

    def __str__(self):
        return f"<SumWave, width: {self.width:e} s>\n" \
               f"{indent(str(self.wave1), '  ')}\n" \
               f"{indent(str(self.wave2), '  ')}"


class CarryWave(Waveform):
    def __init__(self, wave1: Waveform, wave2: Waveform):
        super().__init__(max(wave1.width, wave2.width), 1)
        self.wave1 = wave1
        self.wave2 = wave2

    def at(self, time):
        return np.where(time > self.width, 0, (self.wave1.at(time) * self.wave2.at(time)) * self.amplitude)
        # The default value of self.amplitue is 1. In case of (wave1*wave2)*other, it will be set as other.

    def __str__(self):
        return f"<CarryWave, width: {self.width:e} s>\n" \
               f"{indent(str(self.wave1), '  ')}\n" \
               f"{indent(str(self.wave2), '  ')}"


class Sequence(Waveform):
    def __init__(self, *argv):
        super().__init__(0, 1)
        self.sequence = []
        self.each_waveform_start_at = None

        for arg in argv:
            if isinstance(arg, Sequence):
                self.sequence.extend(arg.sequence)
            elif isinstance(arg, Waveform):
                self.sequence.append(arg)
            else:
                raise TypeError("Expected Waveform")

        self._analysis_each_waveform_start_at()

    def _analysis_each_waveform_start_at(self):
        self.each_waveform_start_at = [0]
        time = 0
        for waveform in self.sequence:
            time += waveform.width
            self.each_waveform_start_at.append(time)
        self.width = time

    def at(self, time):
        if len(self.sequence) == 0:
            return 0
        condlist = []
        choicelist = []
        for i in range(len(self.each_waveform_start_at) - 1):
            condlist.append(
                np.logical_and(time >= self.each_waveform_start_at[i],
                               self.each_waveform_start_at[i] + self.sequence[i].width >= time))
            choicelist.append(self.sequence[i].at(time - self.each_waveform_start_at[i]))
        return np.select(condlist, choicelist, default=0)

    def thumbnail_sample(self, sample_points):
        result = np.zeros(len(sample_points))

        sample_pos = 0
        for i in range(len(self.each_waveform_start_at) - 1):
            start_at = self.each_waveform_start_at[i]
            next_start_at = self.each_waveform_start_at[i + 1]

            while sample_points[sample_pos] < start_at:
                result[sample_pos] = 0
                sample_pos += 1
            if sample_pos == len(sample_points) - 1:
                break

            if sample_points[sample_pos] < next_start_at:
                while sample_points[sample_pos] < next_start_at:
                    result[sample_pos] = self.sequence[i].at(sample_points[sample_pos] - start_at)
                    sample_pos += 1
                    if sample_pos == len(sample_points) - 1:
                        break
            else:
                # If some waveforms has width that is less than the resolution of sample_rate:
                result[sample_pos] = self.sequence[i].at(
                    (start_at + next_start_at) / 2 - start_at)
                sample_pos += 1

            if sample_pos == len(sample_points) - 1:
                break

        return result  # haven't read this part yet, maybe next time!

    def __str__(self):
        _str = f"<Sequence, width: {self.width:e} s>\n"
        for seq in self.sequence:
            _str += indent(str(seq), '  ') + "\n"

        return _str


class Sin(Waveform):
    def __init__(self, width, amplitude, omega=0, phi=0):
        super().__init__(width, amplitude)
        self.omega = omega
        self.phi = phi

    def at(self, time):
        return np.where(time > self.width, 0, self.amplitude * np.sin(self.omega * time + self.phi))

    def __str__(self):
        return f"<Sin, amplitude:{self.amplitude} V, width: {self.width:e} s>"


class Cos(Waveform):
    def __init__(self, width, amplitude, omega=0, phi=0):
        super().__init__(width, amplitude)
        self.omega = omega
        self.phi = phi

    def at(self, time):
        return np.where(time > self.width, 0, self.amplitude * np.cos(self.omega * time + self.phi))

    def __str__(self):
        return f"<Cos, amplitude:{self.amplitude} V, width: {self.width:e} s>"


class ComplexExp(Waveform):
    def __init__(self, width, amplitude, omega=0, phi=0):
        super().__init__(width, amplitude)
        self.omega = omega
        self.phi = phi

    def at(self, time):
        return np.where(time > self.width, 0,
                        self.amplitude * np.cos(self.omega * time + self.phi) + 1j * np.sin(
                            self.omega * time + self.phi))

    def __str__(self):
        return f"<ComplexExp, amplitude:{self.amplitude} V, width: {self.width:e} s>"


class DC(Waveform):
    def __init__(self, width, offset, complex_phi=0):
        super().__init__(width, offset)
        self.complex_phi = complex_phi

    def at(self, time):
        return np.where(time > self.width, 0, self.amplitude)

    def __str__(self):
        return f"<DC, offset:{self.amplitude} V, width: {self.width:e} s>"


class DC_Complex(Waveform):
    def __init__(self, width, offset, complex_phi=0):
        super().__init__(width, offset)
        self.complex_phi = complex_phi

    def at(self, time):
        return np.where(time > self.width, 0, self.amplitude * np.exp(1j * self.complex_phi))

    def __str__(self):
        return f"<DC, offset:{self.amplitude} V, width: {self.width:e} s>"


class Blank(DC):
    def __init__(self, width=0):
        super().__init__(width, 0, 0)

    def __str__(self):
        return f"<Blank, width: {self.width:e} s>"


class Gaussian(Waveform):
    def __init__(self, width=0, amplitude=1):
        super().__init__(width, amplitude)

        self.sigma = width / (4 * np.sqrt(2 * np.log(2)))

    def at(self, time):
        return np.where(time > self.width, 0,
                        self.amplitude * np.exp(-0.5 * ((time - 0.5 * self.width) / self.sigma) ** 2))

    def __str__(self):
        return f"<Gaussian, amplitude:{self.amplitude} V, width: {self.width:e} s>"


class CalibratedIQ(Waveform):
    # This class is designed to generated calibrated IQ waveforms.
    # Calibrated IQ carry wave is generated, and multiplied with (I_waveform + j * Q_waveform)
    # WARNING: This class doesn't deal with channel voltage offset. You should manually set it.
    #          since it should be applied to a channel in the entire time span to compensate the
    #          LO leakage.
    def __init__(self,
                 carry_freq,
                 I_waveform: Waveform = None,
                 Q_waveform: Waveform = None,
                 IQ_cali=None,
                 down_conversion: bool = False  # up conversion: set to True
                 ):
        from thunderq.helper.iq_calibration_container import IQCalibrationContainer
        # assert isinstance(IQ_cali, IQCalibrationContainer)

        super().__init__(0, 1)

        self.omega = 2 * np.pi * carry_freq

        IQ_waveform = None
        if I_waveform is None and Q_waveform:
            IQ_waveform = Q_waveform * 1j
        elif Q_waveform is None and I_waveform:
            IQ_waveform = I_waveform
        elif Q_waveform is None and I_waveform is None:
            raise TypeError("At least one of I waveforms and Q waveforms should be given.")
        else:
            IQ_waveform = I_waveform + (Q_waveform * 1j)

        self.width = IQ_waveform.width
        self.amplitude = IQ_waveform.amplitude

        if down_conversion:
            self.carry_IQ = IQ_waveform * (
                Cos(self.width, 1, self.omega, 0) + Sin(self.width, 1, self.omega, 0) * 1j
            )
        else:
            self.carry_IQ = IQ_waveform * (
                Cos(self.width, 1, self.omega, 0) + Sin(self.width, 1, self.omega, 0) * (-1j)
            )

        self.left_shift_I = 0
        self.left_shift_Q = 0

        self.scale_I = 1
        self.scale_Q = 1
        self.offset_I = 0
        self.offset_Q = 0

        if IQ_cali and carry_freq:
            self.scale_I, self.offset_I = IQ_cali.I_amp_factor, 0  # IQ_cali.I_offset
            self.scale_Q, self.offset_Q = IQ_cali.Q_amp_factor, 0  # IQ_cali.Q_offset

            _phi_I = IQ_cali.I_phase_shift + IQ_cali.I_time_offset * self.omega
            _phi_Q = IQ_cali.Q_phase_shift + IQ_cali.Q_time_offset * self.omega

            # Calculate phase shift, equivalent to time shift
            self.left_shift_I = IQ_cali.I_phase_shift / self.omega + IQ_cali.I_time_offset
            self.left_shift_Q = IQ_cali.Q_phase_shift / self.omega + IQ_cali.Q_time_offset

    def at(self, time):
        I_value = self.carry_IQ.at(time + self.left_shift_I).real
        Q_value = self.carry_IQ.at(time + self.left_shift_Q).imag

        # Amplitude calibration
        I_value = I_value * self.scale_I  # + self.offset_I
        Q_value = Q_value * self.scale_Q  # + self.offset_Q

        return I_value + 1j * Q_value

    def __mul__(self, other):
        raise TypeError("It's unwise to adjust the amplitude of a calibrated waveforms.")

    def __str__(self):
        return f"<CalibratedIQ, width: {self.width:e} s>\n" \
               f"{indent(str(self.carry_IQ), '  ')}"


class Real(Waveform):
    def __init__(self, complex_waveform: Waveform):
        super().__init__(complex_waveform.width, 1)
        self.complex_waveform = complex_waveform

    def at(self, time):
        return self.complex_waveform.at(time).real * self.amplitude

    def __str__(self):
        return f"<Real of {self.complex_waveform}>"


class Imag(Waveform):
    def __init__(self, complex_waveform: Waveform):
        super().__init__(complex_waveform.width, 1)
        self.complex_waveform = complex_waveform

    def at(self, time):
        return self.complex_waveform.at(time).imag * self.amplitude

    def __str__(self):
        return f"<Imag of {self.complex_waveform}>"
