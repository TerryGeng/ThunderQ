# ThunderQ

General time-sequential, waveform-based experiment framework.

## Features

- Designed for experiments utilizing waveforms to operate with physical systems.

- Breaks waveforms across the entire experiment cycle into individual modules 
(i.e. procedures), allows highly flexible module design, and automatically 
assembles modules together.

- Intuitive scan experiment("sweep") function, with realtime figure generation
and data file writer.

- Waveform description classes. Storing waveforms in abstract format, with
a set of methods to manipulate waveforms.

## Dependencies

- [device_repo](https://github.com/TerryGeng/device_repo), the device control
backend. 

- [ThunderBoard](https://github.com/TerryGeng/ThunderBoard), a real-time data
visualization platform.

## Installation

1. Install [device_repo](https://github.com/TerryGeng/device_repo) and 
[ThunderBoard](https://github.com/TerryGeng/ThunderBoard).

2. Install ThunderQ by executing
```bash
pip install --editable .
```
If you use virtual environment, you need to activate it first.

## Documentations

1. [Tutorials](docs/tutorial)

