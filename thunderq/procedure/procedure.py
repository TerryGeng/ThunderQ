from thunderq.helper.sequence import Sequence


class Procedure:
    # Describe the change of waveforms during a time-span.
    # But it can also be used to do other task unrelated to waveforms.

    # Monitor the changes in these attributes, if modified, set self.has_update to True.
    # Useful for sequence helper to determine if it need to recompile the waveform
    __parameters = []

    def __init__(self, name, result_prefix=""):
        self.name = name
        self.has_update = True
        self.result_prefix = result_prefix

    def __setattr__(self, key, value):
        if key in self.__parameters:
            super().__setattr__("has_update", True)
        super().__setattr__(key, value)

    def pre_run(self):
        # Generate the waveform here
        raise NotImplementedError

    def post_run(self):
        # This method is used to fetch the result of this procedure, if this
        # procedure read any acquisition device.
        # Format of the return value: a dict,
        # { self.result_prefix + 'key_of_this_data': data_val }

        raise NotImplementedError
