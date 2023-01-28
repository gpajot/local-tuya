from logging import DEBUG, INFO, Formatter, LogRecord, StreamHandler

try:
    import DomoticzEx
except ModuleNotFoundError:
    from local_tuya.domoticz.types import DomoticzEx


class DomoticzHandler(StreamHandler):
    def __init__(self):
        super().__init__()
        self.setFormatter(Formatter("%(levelname)s: %(name)s: %(message)s"))
        self.setLevel(DEBUG)

    def emit(self, record: LogRecord) -> None:
        msg = self.format(record)
        if record.levelno <= DEBUG:
            DomoticzEx.Debug(msg)
        elif record.levelno <= INFO:
            DomoticzEx.Log(msg)
        else:
            DomoticzEx.Error(msg)
