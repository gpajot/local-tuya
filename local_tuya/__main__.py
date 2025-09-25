import logging.config
import sys

import uvloop

from local_tuya.config import Config
from local_tuya.manager import DeviceManager

config = Config.load()
logging.config.dictConfig(config.logging)
if "-v" in sys.argv or config.debug:
    logging.getLogger().setLevel(logging.DEBUG)

uvloop.run(DeviceManager(config).run())
