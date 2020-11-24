from thunderq.waveform.waveform import Waveform
from thunderq.helper.sequence import Sequence,PaddingPosition
from thunderq.procedure import Procedure
from thunderq.runtime import Runtime
from device_repo import AWG, DG


class RunWaveform(Procedure):
    def __init__(self,
                 runtime: Runtime,
                 slice: Sequence.Slice,
                 channel_dev: AWG,
                 waveform: Waveform,
                 padding_pos=PaddingPosition.PADDING_BEFORE
                 ):
        super().__init__("IQ Modulation")
        self.runtime = runtime
        self.slice = slice
        self.channel_dev = channel_dev
        self.waveform = waveform
        self.has_update = True
        self.padding_pos = padding_pos

    def set_waveform(self, waveform: Waveform):
        self.waveform = waveform
        self.has_update = True

    def pre_run(self):
        if self.has_update:
            self.slice.add_waveform(self.channel_dev, self.waveform)
            self.slice.set_waveform_padding(self.channel_dev, self.padding_pos)

            self.has_update = False

    def post_run(self):
        pass

