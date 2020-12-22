# ThunderQ Tutorials

This section includes a series of tutorials that let you quickly
get started with ThunderQ.

## Terminologies and Concepts

- **Waveform-based experiment**: Waveform-based experiments usually utilize 
delay generators("trigger"), waveform generators, and analog signal generators to
operate a physical system in a short period of time. Rather than the PC command
each device step by step, waveform-based experiments require PC to "compile"
the waveforms and the time sequence first, then using "triggers" and waveform
generators to run an experiment.

- **Channel**: Usually, waveform-based experiments need to produce different
waveforms at different cables simultaneously. Each cable connects to different
port of the same waveform generator or different waveform generators. Each
port of the waveform generator is considered to be a _channel_ of it.

- **Sequence**: A _sequence_ is a timespan that a cycle of one 
experiments runs on, usually involves a bunch of channels triggered at different
time of the cycle.

- **Slice**: A sequence is composed by _slices_. A slice is a particular 
part of a sequence, marked by its start time and duration. In ThunderQ,
the `Sequence` class stores all slices and is in charge of composing the
waveforms among slices into the actually waveform performed by the waveform
generator.  A slice can be made up of a series of sub-slice.

- **Procedure**: A _procedure_ is a set of operations and waveforms to execute
within slices. In general cases, people pass slices into procedures as parameter
and let procedures write their own waveforms into slices. The benefit is: the
procedures don't need to worry about other waveforms in the sequence, and don't
have to care about align waveform across channels.

- **Cycle**: A cycle is a set of procedures performed after the triggered has 
been triggered once. One experiment usually repeatedly performs a cycle many 
times, with some parameters to be different each time ("scan" experiment or 
"sweep" experiment).

# Contents
1. [Tutorial1. My First Experiment](toturial1.md)
