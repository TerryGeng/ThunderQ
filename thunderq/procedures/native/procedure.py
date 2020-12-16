class Procedure:
    # Describe the change of waveforms during a time-span.
    # But it can also be used to do other task unrelated to waveforms.

    # Monitor the changes in these attributes, if modified, set self.has_update to True.
    # Useful for sequence helper to determine if it need to recompile the waveforms
    _parameters = []
    _parameter_alias = {}
    _result_keys = []

    def __init__(self, name, result_prefix=""):
        self.name = name
        self.has_update = True
        self.result_prefix = result_prefix
        self.modified_params = []

    def __setattr__(self, key, value):
        if key in self._parameter_alias:
            param = self._parameter_alias[key]
        else:
            param = key
        if param in self._parameters:
            super().__setattr__("has_update", True)
            if param not in self.modified_params:
                self.modified_params.append(param)
        super().__setattr__(param, value)

    def pre_run(self):
        # Generate the waveforms here
        raise NotImplementedError

    def post_run(self):
        # This method is used to fetch the result of this procedures, if this
        # procedures read any acquisition device.
        # Format of the return value: a dict,
        # { self.result_prefix + 'key_of_this_data': data_val }

        raise NotImplementedError
