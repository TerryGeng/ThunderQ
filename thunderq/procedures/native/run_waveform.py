from thunderq.waveforms.native.waveform import Waveform
from thunderq.sequencer.slices import PaddingPosition, Slice
from thunderq.procedures.native import Procedure
from thunderq.runtime import Runtime


class RunWaveform(Procedure):
    _parameters = ["waveform"]

    def __init__(self,
                 runtime: Runtime,
                 slice: Slice,
                 channel_dev,
                 waveform: Waveform,
                 padding_pos=PaddingPosition.PADDING_BEFORE
                 ):
        super().__init__("Waveform")
        self.runtime = runtime
        self.slice = slice
        self.channel_dev = channel_dev
        self.waveform = waveform
        self.padding_pos = padding_pos

    def pre_run(self):
        if self.has_update:
            self.slice.add_waveform(self.channel_dev, self.waveform)
            self.slice.set_waveform_padding(self.channel_dev, self.padding_pos)

            self.has_update = False

    def post_run(self):
        pass

