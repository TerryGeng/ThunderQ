class Procedure:
    # Describe the change of waveforms during a time-span.
    # But it can also be used to do other task unrelated to waveforms.

    def __init__(self, name):
        self.name = name

    def pre_run(self):
        raise NotImplementedError

    def post_run(self):
        raise NotImplementedError

    def snapshot(self):
        raise NotImplementedError

    # TODO: Sequence, Time span
