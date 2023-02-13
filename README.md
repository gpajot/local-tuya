# local-tuya

[![tests](https://github.com/gpajot/local-tuya/workflows/Test/badge.svg?branch=main&event=push)](https://github.com/gpajot/local-tuya/actions?query=workflow%3ATest+branch%3Amain+event%3Apush)
[![version](https://img.shields.io/pypi/v/local-tuya?label=stable)](https://pypi.org/project/local-tuya/)
[![python](https://img.shields.io/pypi/pyversions/local-tuya)](https://pypi.org/project/local-tuya/)

Interface to Tuya devices over LAN.

Features:
- asynchronous methods and transport
- persistent communication to the device
- automatic remote device state updates (remotes can still be used)
- configuratble of buffering for subsequent updates
- constraints between device commands
- Domoticz plugin using a dedicated thread

> 💡 For now, only v3.3 is supported as I only own devices using this version.

## Requirements
To control a device you will need these 3 things:
- the device ID
- the device local IP address
- the device local key (encryption key generated upon pairing)

> ⚠️ This library does not provide support for getting these.
> See how to do that using any of those projects:
> - [tuyapi](https://github.com/codetheweb/tuyapi)
> - [tinytuya](https://github.com/jasonacox/tinytuya)
> 
> Generous thanks to the maintainers of those tools for details on interfacing with Tuya devices.

> ⚠️ Keep in mind that:
> - After pairing the devices, it's recommended to assign static IPs in your router.
> - If you reset or re-pair devices the local key will change.
> - You can delete your tuya IOT account but not the SmartLife one and devices should be kept there.
> - For state updates to be received properly, the device needs to be able to access the Tuya backend.

## Architecture
This library is composed of two main components:
- the Tuya protocol
- the device

### Protocol
The protocol is responsible for handling communication details with the Tuya device.
Its interface consists of an asynchronous method to update the device and accepts a callback to subscribe to state changes.

See [protocol module](./local_tuya/protocol).

### Device
The device handles higher level functional logic such as buffering, constraints and specific device commands.

See [device module](./local_tuya/device).

## Domoticz plugin tools
See [Domoticz module](./local_tuya/domoticz).
