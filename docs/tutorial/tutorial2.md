## Tutorial2. Run Cycle with Sweep Engine

> Demo code available at [tutorial2.py](tutorial2.py)

Usually running a cycle once cannot be considered to be a meaningful scientific
experiment. People care about the response of a physical system under different
input parameters. It involves _scanning_ through one parameters and acquiring
a graph of the response parameter against the response.

Generally, one can always use a `for` loop and call `cycle.run()` inside, but
just to make people's lives easier, _ThunderQ_ introduced a helpful `sweep`
engine to conduct such experiment.

> Using _sweep_ instead of _scan_ is actually a misuse of English.
> But the funny picture of _sweeping_ something make the author decided to stick
> with this expression.

### Write a cycle for scanning

To begin with, let's write a somewhat interesting a procedure to draw a sine
wave on one channel and a DC bias waveform on the other channel.
```python
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

        # generate sin waveform
        sin_waveform = Sin(width=self.duration,
                           amplitude=self.sin_amplitude,
                           omega=2*math.pi*self.sin_frequency)

        # remove old waveform from the channel
        self.slice.clear_waveform(self.sin_channel)
        self.slice.add_waveform(self.sin_channel, sin_waveform)

        # generate bias waveform
        bias_waveform = DC(self.duration, self.bias_offset)

        self.slice.clear_waveform(self.bias_channel)
        self.slice.add_waveform(self.bias_channel, bias_waveform)

    def post_run(self):
        pass
```

This time we'd like to acquire some data after waveforms have been performed.
We utilize the `post_run` method inside a procedure and create a procedure like
```python
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
        time.sleep(1)  # simulate the time consumed when acquiring data
        ret = self.digitizer.fetch_average()
        return {
            'ch1_amplitude': ret[0][0],
            'ch2_amplitude': ret[1][0]
        }
```

Combining these two procedures, we create a cycle:
```python
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
```

This cycle simply combines these two procedures together.


### Run the cycle, and retain its return value

Now we may run this cycle with some mock devices:
```python
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
```

As explained in the code, this time we directly import the ready-to-use mock
devices from `mock_device`, with a new device called `mock_random_digitizer`.
This simulated device simulate a Analog-to-Digital Converter(ADC) that convert
input voltage into a number we can read on the PC (in this case it just generate
random number).

We run the cycle by hitting
```python
ret = cycle.run()
```

But this time, since one procedure actually _returns_ something, we can save the
return value into `ret` and print it out with `print(ret)`
```json
{"ch1_amplitude": 5, "ch2_amplitude": 1}
```

We can also utilize the internal logger of ThunderQ by
```python
runtime.logger.log(ret)
```
then you will see a Log window shows up in the _ThunderBoard_ with the log 
message in it.


### Scan the cycle with sweep engine

Now assume we want to scan the parameter `sin_frequency` and see the amplitude
of our digitizer when `sin_frequency` changes.
We simply import the sweep engine, initialize it and call `.sweep(...)` to run it.

```python
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
```

As the above code shows, the `scam_param` is the actual parameter that you'd like
to scan (the scan axis). `points` is a series of points that `scan_param` need to
walk through. `result_name` is the actual result that needs to be plotted and saved.

After running this code, you will see a plot window shown in the _ThunderBoard_,
and the sequence plot reflects the change of `sin_frequency`.

If you open the `data/` folder, you will discover two `.txt` files and one image
are generated. These are the scan result of this sweep. One of these `.txt` that
ends with `params.txt` is the other parameters used in running this scan.
The sweep engine will read the `_parameters` attribute of the procedure to
determine which attribute counts as a parameter to be saved.

It can be open with Excel, Matlab or you can have your own python program to
process these results.


### Rewrite waveform or not?

In real world scenario, writing waveform to waveform generators can be time
consuming. If we rewrite the every waveform for each cycle, the rewrite itself
will waste a lot of time.

The sequencer is designed to keep track of the status of waveforms in each 
slice, and only rewrite a channel when something in this channel actually
_changed_. If no new waveform has been written to the channel since the list
time, the channel won't be write. We need to utilize this mechanism to avoid
frequent and unnecessary rewrite.

The `Procedure` also helps you know what is changed between each `pre_run`.
Simply put, it will monitor all attributes in `_parameters`.
And in `pre_run`, you can read `modified_params` to get a list of modified
parameters:
```python
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
            
        self.modified_params = []  # remember to clean it!
```

In the scan we designed above, the offset value of the bias channel doesn't
change. After adding these conditional statements, you will avoid rewrite
bias channel each time the `sin_frequency` is changed.


### Summary
In this tutorial, we learned:
1. How to build procedures and cycle that is suitable for scanning.
2. See `FixedLengthSlice` comes into play.
3. How to invoke the sweep engine, and the way it behaviors.
4. How to avoid waveform rewrite by using `_parameters` and `modified_params`.


### Homework
1. Try to scan with other parameters like `sin_amplitude` or `bias_offset`.