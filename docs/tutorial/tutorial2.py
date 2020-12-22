from thunderq.procedures.native import Procedure
from thunderq.cycles.native import Cycle


class BiasedSinProcedure(Procedure):
    # This procedure generate a sine wave and a DC bias waveform on two channels
    # It should give something like
    # sine channel .../-\_/-\_/...
    # bias channel ...---------...

    _parameters = ['sin_amplitude', 'sin_frequency', 'bias_offset']

    def __init__(self, name, sin_channel, bias_channel, slice, duration):
        super().__init__(name)
        self.sin_channel = sin_channel
        self.bias_channel = bias_channel
        self.slice = slice
        self.duration = duration

        self.sin_amplitude = 0
        self.sin_frequency = 0
        self.bias_offset = 0

    def pre_run(self):
        import math
        from thunderq.waveforms.native.waveform import DC, Sin

        # detect if parameters has been updated and we need to write the
        # waveform
        if 'sin_amplitude' in self.modified_params or \
                'sin_frequency' in self.modified_params:
            # generate sin waveform
            sin_waveform = Sin(width=self.duration,
                               amplitude=self.sin_amplitude,
                               omega=2*math.pi*self.sin_frequency)

            # remove old waveform from the channel
            self.slice.clear_waveform(self.sin_channel)
            self.slice.add_waveform(self.sin_channel, sin_waveform)

        if 'bias_offset' in self.modified_params:
            # generate bias waveform
            bias_waveform = DC(self.duration, self.bias_offset)

            self.slice.clear_waveform(self.bias_channel)
            self.slice.add_waveform(self.bias_channel, bias_waveform)

        self.modified_params = []

    def post_run(self):
        pass


class PureAcquisitionProcedure(Procedure):
    # this procedure will simply acquire some data from a digitizer
    # in post_run
    # digitizer is a type of acquisition device
    def __init__(self, name, digitizer):
        super().__init__(name)
        self.name = name
        self.digitizer = digitizer

    def pre_run(self):
        # no waveform needed to be written
        pass

    def post_run(self):
        # post_run method may return a dict as its result, with the key to be
        # the name of the result
        import time
        time.sleep(1)
        ret = self.digitizer.fetch_average()
        return {
            'ch1_amplitude': ret[0][0],
            'ch2_amplitude': ret[1][0]
        }


class BiasSinCycle(Cycle):
    def __init__(self, sin_channel, bias_channel, slice, duration, digitizer,
                 sequence):
        # sequence: the `sequence` object that holds all channels and slices
        super().__init__("Bias Sin Cycle", sequence)
        self.bias_sin_procedure = BiasedSinProcedure("bias_sin_procedure1",
                                                     sin_channel, bias_channel,
                                                     slice, duration)
        self.add_procedure(self.bias_sin_procedure)
        self.acquisition_procedure = PureAcquisitionProcedure("acquisition",
                                                              digitizer)
        self.add_procedure(self.acquisition_procedure)


# Start to describe experiment setup

# import mock devices
# actually there're ready to use mock devices that have been wrapped with
# AWGChannel, this time we just directly import them here.
# mock_random_digitizer is a simulated digitizer that will give some random
# readings
from thunderq.helper.mock_devices import mock_awg0, mock_awg1, mock_dg, \
    mock_random_digitizer

from thunderq.runtime import Runtime

runtime = Runtime()
sequence = runtime.create_sequence(mock_dg, 100000)
sequence.add_trigger("test_trigger_0", 0, 0, 1e-6) \
    .link_waveform_channel("channel_0", mock_awg0) \
    .link_waveform_channel("channel_1", mock_awg1)

# define slices
# this time we try another type of slice called FixedLengthSlice
# whose length won't change with waveform
from thunderq.sequencer import FixedLengthSlice, PaddingPosition
slice_a = FixedLengthSlice("slice_a", duration=10e-6)  # lasts 10us

# for FixedLengthSlice, if the waveform is not long enough to fill the
# whole slice, padding will be added
# by default, padding will be added to the beginning of the channel.
# you can change this behavior by adding these two lines
slice_a.set_waveform_padding(mock_awg0, PaddingPosition.PADDING_BEHIND)
slice_a.set_waveform_padding(mock_awg1, PaddingPosition.PADDING_BEHIND)

sequence.add_slice(slice_a)

cycle = BiasSinCycle(sin_channel=mock_awg0,
                     bias_channel=mock_awg1,
                     slice=slice_a,
                     duration=5e-6,
                     digitizer=mock_random_digitizer,
                     sequence=sequence)

# initialize procedure's parameters
cycle.bias_sin_procedure.sin_frequency = 1e6
cycle.bias_sin_procedure.sin_amplitude = 1
cycle.bias_sin_procedure.bias_offset = 1

ret = cycle.run()

# print the result with the _logger_ inside runtime
# print(ret)
runtime.logger.log(ret)


# construct a scan
from thunderq.experiment import Sweep1DExperiment
import numpy as np
exp = Sweep1DExperiment(runtime, "SinFrequencyScan", cycle)

# just to make the sequence plot more precise
# usually it is 1e6
# turning it into 1e9 is simply for this demonstration
sequence.sequence_plot_sample_rate = 1e9

exp.sweep(scan_param="bias_sin_procedure.sin_frequency",
          points=np.linspace(0.5e6, 1.5e6, 11),
          scan_param_unit="arb.",
          result_name='ch1_amplitude')
