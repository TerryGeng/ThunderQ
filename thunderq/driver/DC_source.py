class DCChannel:
    def __init__(self, _name, _rc, _ch):
        self.rc = _rc
        self.name = _name
        self.channel = _ch

    def set_offset(self, offset):
        self.rc.setValue('Offset', ch=self.channel, value=offset)
