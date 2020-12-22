## Tutorial1. My First Experiment

> Demo code available at [tutorial1.py](tutorial1.py)

The purpose of this tutorial is to quickly let the reader grasp the _feel_ of
writing experiments with ThunderQ and understand some basic concepts.
We are going to start with a simple experiment that doesn't make much sense 
scientifically: we would like to perform three square waves on three different 
waveform _channels_ consecutively.

The sequence of this simple experiment can be drawn as:
```
Channel 1 -------______________
Channel 2 _______-------_______
Channel 3 ______________-------
```

Let's divide this sequence into three slices as follows:
```
Channel 1 |-------|_______|_______|
Channel 2 |_______|-------|_______|
Channel 3 |_______|_______|-------|
           Slice A Slice B Slice C
```

As shown in this figure, in each slice, there's one channel that is filled
with a square wave.

### Begin with procedure

To write down this experiment, the first building block we need is a _procedure_
to add a square wave to a channel in one slice. Such procedure could be done by

```python
from thunderq.procedures.native import Procedure

class SquareWaveProcedure(Procedure):
    def __init__(self, name, channel, slice, amplitude, duration):
        # arguments explained:
        # - name: the name of this procedure
        # - channel: the channel where this square wave should be performed
        # - slice: the slice where this square wave should be performed
        # - amplitude: the amplitude of this square wave
        # - duration: the duration of this square wave

        super().__init__(name)
        self.channel = channel
        self.slice = slice
        self.amplitude = amplitude
        self.duration = duration

    def pre_run(self):
        # this method is in charge of preparing all waveforms for this procedure,
        # and write them into slices. It will be called before waveforms are
        # written into each channels.

        # create a square wave
        from thunderq.waveforms.native.waveform import DC
        waveform = DC(self.duration, self.amplitude)
        
        # add this square wave to self.channel at self.slice
        self.slice.add_waveform(self.channel, waveform)

    def post_run(self):
        # this method will be called after one cycle has been done (all waveform
        # in all slices has been written into channels and been performed)

        # for SquareWaveProcedure, it doesn't need to do anything here.
        pass
```

### Put procedures into cycle

Now we have a procedure that writes a square wave into a channel. Now we need to 
prepare a _cycle_ to write three square waves into three channels. Let's call
such cycle to be `TripleSquareWaveCycle`.

```python
from thunderq.cycles.native import Cycle

class TripleSquareWaveCycle(Cycle):
    def __init__(self, square_wave_length, square_wave_amp,
                 channel1, channel2, channel3,
                 slice1, slice2, slice3, sequence):
        # sequence: the `sequence` object that holds all channels and slices
        super().__init__("Triple Square Wave Cycle", sequence)
        self.square_wave1 = SquareWaveProcedure("SquareWave1", 
                                                channel1,
                                                slice1,
                                                square_wave_amp, 
                                                square_wave_length)
        self.add_procedure(self.square_wave1)

        self.square_wave2 = SquareWaveProcedure("SquareWave2", 
                                                channel2,
                                                slice2,
                                                square_wave_amp, 
                                                square_wave_length)
        self.add_procedure(self.square_wave2)

        self.square_wave3 = SquareWaveProcedure("SquareWave3", 
                                                channel3,
                                                slice3,
                                                square_wave_amp, 
                                                square_wave_length)
        self.add_procedure(self.square_wave3)
```

### Describe experiment setup

After completing the cycle, we may try to run it. But before that, we need to
specify the experiment setup first.

For demonstration purpose, several _mock_ device has been prepared. You can use
them as if they are real devices connected to your PC. We just invoke them here.

```python
# import channel and trigger wrapper from sequencer
from thunderq.sequencer import AWGChannel, DGTrigger

# import mock devices
from thunderq.helper.mock_devices import MockAWG, MockDG

# create three waveform channels with MockAWG
mock_awg0 = AWGChannel("mock_awg0", MockAWG("mock_awg0"))
mock_awg1 = AWGChannel("mock_awg1", MockAWG("mock_awg1"))
mock_awg2 = AWGChannel("mock_awg2", MockAWG("mock_awg2"))

# create trigger from mock delay generator
mock_dg = DGTrigger(MockDG())

from thunderq.runtime import Runtime

# runtime saves some common components used in an experiment like its sequence,
# the logger, and some configurations, etc.
runtime = Runtime()

# set the frequency of this DG to be 100000 Hz (10us per cycle)
sequence = runtime.create_sequence(mock_dg, 100000)
# set the position of the edge of trigger line 0: to raise at 0 and drop after 1us
sequence.add_trigger("test_trigger_0", 0, 0, 1e-6) \
    .link_waveform_channel("channel_0", mock_awg0) \
    .link_waveform_channel("channel_1", mock_awg1) \
    .link_waveform_channel("channel_2", mock_awg2) # link channels that are triggered by this edge

# define three slices
from thunderq.sequencer import FlexSlice

# FlexSlice doesn't has a fixed start point and length
# it's start point is determined by slices before it, while its length depends
# on the waveform in it.
slice_a = FlexSlice("slice_a")
slice_b = FlexSlice("slice_b")
slice_c = FlexSlice("slice_c")

# add slices into sequence
sequence.add_slice(slice_a)
sequence.add_slice(slice_b)
sequence.add_slice(slice_c)
```

### Run cycle with experiment setup

Now we can run the cycle defined before with the setup above:
```python
cycle = TripleSquareWaveCycle(
            square_wave_length=3e-6, 
            square_wave_amp=1,
            channel1=mock_awg0, 
            channel2=mock_awg1, 
            channel3=mock_awg2, 
            slice1=slice_a,
            slice2=slice_b,
            slice3=slice_c,
            sequence=sequence)

# run the entire cycle
cycle.run()
```

ThunderQ will help you deal with compiling the real waveform executed in each 
channel (with appropriate padding), and set the trigger up with the
configuration you have specified.

To check the result, You need to start the _ThunderBoard_ first (by running 
`thunderboard` in commandline and open http://127.0.0.1:2334/ in your browser)
first to receive the sequence graph.
After running all the code above, you will see the sequence plot posted to
the _ThunderBoard_.

![Sequence Plot with sample rate 1e6](images/sequence_example1.png)

The sequence plot may look a little bit distorted. That is due to the 
down-sampling process used in sequence plot generating. To produce a precise 
sequence plot, you can specify the precision of the sequence plot by
```python
sequence.send_sequence_plot(plot_sample_rate=1e9)
```

![Sequence Plot with sample rate 1e9](images/sequence_example2.png)

You can also access the waveforms written into the MockAWG by executing
```python
mock_awg0.device.plot_waveform(runtime.logger)
```

### Summary

In this tutorial, we learned:
1. What is a procedure, a cycle.
2. How to write a square wave with the `Waveform` class and turn waveforms into
procedures.
3. How to tell ThunderQ about your experimental setup.
4. How to create _slices_ (though only `FlexSlice` is introduced).
4. How to use mock devices.

### Homework

1. With the `TripleSquareWaveCycle` above, move the square wave of `mock_awg0` 
on `slice_a` to `mock_awg2`.

2. Python challenges: Write a `MultipleSquareWaveCycle` to write square wave to
unlimited number of channels.

