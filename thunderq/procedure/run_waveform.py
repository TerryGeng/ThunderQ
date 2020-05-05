from thunderq.helper.waveform import WaveForm
from thunderq.helper.sequence import Sequence
from thunderq.procedure import Procedure
import thunderq.runtime as runtime

class RunWaveform(Procedure):
    def __init__(self,
                 slice_name: str,
                 channel_name: str
                 ):
        super().__init__("IQ Modulation")
        self.slice_name = slice_name
        self.channel_name = channel_name
        self.waveform = None

    def set_waveform(self, waveform: WaveForm):
        self.waveform = waveform

    def pre_run(self, sequence: Sequence):
        assert self.waveform, 'Waveform is None!'

        slice: Sequence.Slice = sequence.slices[self.slice_name]
        slice.add_waveform(self.channel_name, self.waveform)
        slice.set_waveform_padding(self.channel_name, Sequence.PADDING_BEFORE)

    def post_run(self):
        pass

