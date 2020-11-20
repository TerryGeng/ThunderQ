from typing import List, Union
from device_repo import AWG
from thunderq.waveform.waveform import DC
from thunderq.helper.sequence import Sequence
from thunderq.runtime import Runtime
from thunderq.procedure import Procedure


class FluxAtSlice(dict):
    def __init__(self, slice: Sequence.Slice):
        super().__init__()
        self.slice = slice

    def set_channel_flux(self, channel_dev, flux_value):
        self[channel_dev] = flux_value


class FluxDynamicBias(Procedure):
    def __init__(self, runtime: Runtime, default_flux: FluxAtSlice):
        super().__init__("IQ Modulation")
        self.flux_channels = list(default_flux.keys())
        self.slices = []
        self.flux_bias_per_slice = {}
        self.flux_bias_default = default_flux

        self.runtime = runtime

        self.has_update = True

    def set_bias_at_slice(self, bias_voltages_dict: FluxAtSlice):
        self.slices.append(bias_voltages_dict.slice)
        self.flux_bias_per_slice[bias_voltages_dict.slice] = bias_voltages_dict
        for ch in bias_voltages_dict.keys():
            if ch not in self.flux_channels:
                self.flux_channels.append(ch)
                self.flux_bias_default.set_channel_flux(ch, 0)

        self.has_update = True

    def pre_run(self):
        if self.has_update:  # TODO: determine this in sequence helper
            for channel_dev in self.flux_channels:
                if channel_dev in self.flux_bias_default:
                    default_bias = self.flux_bias_default[channel_dev]
                    channel_dev.set_offset(default_bias)
                else:
                    self.flux_bias_default[channel_dev] = 0
                    channel_dev.set_offset(0)

            for slice in self.slices:
                for channel_dev in self.flux_bias_per_slice[slice]:
                    default_bias = self.flux_bias_default[channel_dev]
                    channel_offset = self.flux_bias_per_slice[slice][channel_dev] - default_bias
                    slice.clear_waveform(channel_dev)
                    if channel_offset != 0:
                        slice.add_waveform(channel_dev, DC(width=slice.duration, offset=channel_offset))

            self.has_update = False

    def post_run(self):
        pass

