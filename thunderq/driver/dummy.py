import thunderq.runtime as runtime

class Dummy(dict):
    def __init__(self, name="Dummy"):
        super().__init__()
        self.name = name
        self.last_called = ""

    def __getattr__(self, attr):
        if attr not in self:
            self.last_called = attr
            return self.dummy_function
        else:
            return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

    def dummy_function(self, *args, **kwargs):
        runtime.logger.debug(f"Dummy {self.name}: *{self.last_called}* called, with params {args}, {kwargs}")

    def raise_exception(self):
        raise NotImplementedError

    def get_self(self):
        return self
