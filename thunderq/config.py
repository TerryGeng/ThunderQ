from enum import Enum


class Config:
    class LogOutputType(Enum):
        THUNDERBOARD = 0
        STDOUT = 1
        DISABLED = 10

    def __init__(self):
        self.logging_level = "INFO"
        self.show_sequence = True
        self.log_output_type = Config.LogOutputType.THUNDERBOARD
