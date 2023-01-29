# local-tuya
Interface to Tuya devices over LAN.

Features:
- asynchronous methods and transport
- persistent communication to the device
- automatic remote device state updates (remotes can still be used)
- configuratble of buffering for subsequent updates
- constraints between device commands
- Domoticz plugin using a dedicated thread

> 💡 For now, only v3.3 is supported as I only own devices using this version.

> ⚠️ This library does not provide support for getting the local key of the device.
> See how to do that using any of those projects:
> - [tuyapi](https://github.com/codetheweb/tuyapi)
> - [tinytuya](https://github.com/jasonacox/tinytuya)
> 
> Generous thanks to the maintainers of those tools for details on interfacing with Tuya devices.


## Architecture
This library is composed of two main components:
- the Tuya protocol
- the device

### Protocol
The protocol is responsible of handling communication details with the Tuya device.
Its interface consists of an asynchronous method to update the device and accepts a callback to subscribe to state changes.

See [protocol module](./local_tuya/protocol).

### Device
The device handles higher level functional logic such as buffering, constraints and specific device commands.

See [device module](./local_tuya/device).

## Domoticz plugin tools
See [Domoticz module](./local_tuya/domoticz).
