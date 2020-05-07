import thunderq.runtime as runtime

class Dummy:
    def __init__(self, name="Dummy"):
        super().__setattr__('name', name)
        super().__setattr__('last_called', '')
        super().__setattr__('_dict', {})

    def __getattr__(self, attr):
        if attr not in self._dict:
            self.last_called = attr
            return self.dummy_function
        else:
            return self._dict[attr]

    def __setattr__(self, attr, value):
        self._dict[attr] = value

    def dummy_function(self, *args, **kwargs):
        runtime.logger.debug(f"Dummy {self.name}: *{self.last_called}* called, with params {args}, {kwargs}")

    def raise_exception(self):
        raise NotImplementedError

    def get_self(self):
        return self
