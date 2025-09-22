import asyncio
import sys

from local_tuya.manager import DeviceManager

asyncio.run(DeviceManager(debug="-v" in sys.argv).run())
