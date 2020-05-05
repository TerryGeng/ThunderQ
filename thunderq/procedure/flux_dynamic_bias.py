from thunderq.helper.waveform import WaveForm, DC
from thunderq.helper.sequence import Sequence
from thunderq.procedure import Procedure
import thunderq.runtime as runtime

class FluxDynamicBias(Procedure):
    def __init__(self,
                 flux_channel_names: list,
                 default_bias: dict=None
                 ):
        super().__init__("IQ Modulation")
        self.flux_channel_names = flux_channel_names
        self.slices = []
        self.flux_bias_per_slice = {}
        self.flux_bias_default = default_bias

    def set_bias_at_slice(self, slice_name, bias_voltages_dict: dict):
        self.slices.append(slice_name)
        self.flux_bias_per_slice[slice_name] = bias_voltages_dict

    def pre_run(self, sequence: Sequence):
        for slice_name in self.slices:
            slice: Sequence.Slice = sequence.slices[slice_name]
            for channel_name in self.flux_channel_names:
                if channel_name in self.flux_bias_per_slice[slice_name]:
                    channel_offset = self.flux_bias_per_slice[slice_name][channel_name]
                else:
                    assert self.flux_bias_default, f'Undefined flux bias value for channel {channel_name} at slice {slice_name}!'
                    channel_offset = self.flux_bias_default[channel_name]

                slice.add_waveform(channel_name, DC(width=slice.duration, offset=channel_offset))

    def post_run(self):
        pass

