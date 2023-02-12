from logging import DEBUG, INFO, WARNING, Formatter, LogRecord, StreamHandler

try:
    import DomoticzEx
except ModuleNotFoundError:
    from local_tuya.domoticz.types import DomoticzEx


class DomoticzHandler(StreamHandler):
    """Log handler to send to Domoticz logger."""

    def __init__(self):
        super().__init__()
        self.setFormatter(Formatter("%(levelname)s: %(name)s: %(message)s"))

    def emit(self, record: LogRecord) -> None:
        msg = self.format(record)
        if record.levelno < DEBUG:
            DomoticzEx.Debug(msg)
        elif record.levelno < INFO:
            DomoticzEx.Log(msg)
        elif record.levelno < WARNING:
            DomoticzEx.Status(msg)
        else:
            DomoticzEx.Error(msg)
