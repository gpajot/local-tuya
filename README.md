# local-tuya

[![tests](https://github.com/gpajot/local-tuya/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/gpajot/local-tuya/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)
[![PyPi](https://img.shields.io/pypi/v/local_tuya?label=stable)](https://pypi.org/project/local_tuya/)
[![python](https://img.shields.io/pypi/pyversions/local_tuya)](https://pypi.org/project/local_tuya/)
[![DockerHub](https://img.shields.io/docker/v/gpajot/local-tuya/latest)](https://hub.docker.com/r/gpajot/local-tuya)

Control Tuya devices with MQTT over LAN.

- [Features](#features)
- [Supported devices](#supported-devices)
- [Installation](#installation)
- [Architecture](#architecture)

## Features
- fully asynchronous
- persistent and robust communication to the device and to MQTT
- [MQTT discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
- automatic remote device state updates (remotes can still be used)
- configurable buffering for subsequent updates
- constraints between device commands

> [!IMPORTANT]
> For now, only v3.3 is supported as I only own devices using this version.

## Supported devices
- [Airton AC](./local_tuya/contrib/airton_ac.py)
- [Ceiling Fan](./local_tuya/contrib/ceiling_fan.py)

## Installation

The easiest way is to use the Docker image:

```commandline
docker run -v {PATH_TO_CONFIG}:/app/conf.yaml:ro gpajot/local-tuya
```

Alternatively, you can use the python package and run directly: `CONFIG=path/to/config python -m local-tuya.manager`

### Configuration

The minimal config is:
```yaml
mqtt:
  discovery_prefix: {YOUR_PREFIX_HERE}
  hostname: 127.0.0.1
devices:
  - name: My AC
    model: Airton AC
    config:
      tuya:
        id_: {DEVICE_ID_HERE}
        address: {DEVICE_IP_HERE}
        key: {DEVICE_KEY_HERE}
```

To control a device you will need these 3 things:
- the device ID
- the device local IP address
- the device local key (encryption key generated upon pairing)

> [!IMPORTANT]
> This library does not provide support for getting these.
> See how to do that using any of those projects:
> - [tuyapi](https://github.com/codetheweb/tuyapi)
> - [tinytuya](https://github.com/jasonacox/tinytuya)
> 
> Generous thanks to the maintainers of those tools for details on interfacing with Tuya devices.

> [!WARNING]
> Keep in mind that:
> - After pairing the devices, it's recommended to assign static IPs in your router.
> - If you reset or re-pair devices the local key will change.
> - You can delete your tuya IOT account but not the SmartLife one and devices should be kept there.
> - It looks like you can block the device access to internet from your router and still have it working.

## Architecture
This library is composed of three main components:
- the Tuya protocol
- the device
- the MQTT client

### Tuya protocol
The Tuya protocol is responsible for handling communication details with the Tuya device.
Its interface consists of an asynchronous method to update the device and exposes state changes via events.

See [protocol module](./local_tuya/tuya).

### Device
The device handles higher level functional logic such as buffering, constraints and specific device commands.

See [device module](./local_tuya/device).

### MQTT client
Communication with home hubs through MQTT, supporting auto discovery.

See [mqtt module](./local_tuya/mqtt).

