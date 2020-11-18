import thunderq.runtime as runtime


class Dummy:
    def __init__(self, name="Dummy"):
        super().__setattr__('_dict', {})
        self.name = name
        self.last_called = ''

    def __getattr__(self, attr):
        if attr not in self._dict:
            self.last_called = attr
            return self.dummy_function
        else:
            return self._dict[attr]

    def __setattr__(self, attr, value):
        self._dict[attr] = value

    def dummy_function(self, *args, **kwargs):
        name = self.name
        last_called = self.last_called
        runtime.logger.debug(f"Dummy {name}: *{last_called}* called, with params {args}, {kwargs}")

    def raise_exception(self):
        raise NotImplementedError

    def get_self(self):
        return self
