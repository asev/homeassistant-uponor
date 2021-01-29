# homeassistant-uponor

[![Buy me a smoothie](https://img.shields.io/badge/Buy%20me%20a-smoothie-blue?style=for-the-badge&logo=PAYPAL)](https://www.paypal.me/asev)

Uponor Smatrix Pulse heating system integration for Home Assistant.

## Supported devices

This integration communicates with Uponor Smatrix Pulse communication module R-208.
It should work with all controllers that support this module.

## Installation

1. Startup and configure your system on Uponor Smatrix mobile app. Make sure you are able to control heating via the app.
System has to be connected to the local network and you should know it's IP address.

2. Install "Uponor Smatrix Pulse" integration on HACS

OR copy the custom_components folder to your own Home Assistant /config folder.

3. Enable the component by adding the following in your `configuration.yml`:
```yaml
uponor:
    host: IP_ADDRESS_OF_UPONOR_DEVICE
```
4. Restart Home Assistant server
   
## Structure

Separate entity `climate.THERMOSTAT_NAME` will be created for every thermostat.
Thermostat names can be changed in Uponor Smatrix app or via configuration.

`switch.uponor_away` controls away mode. It activates ECO mode for all thermostat.

## Configuration

- `names` : map (optional) - custom name for every thermostat. `C1_T1` is the thermostat id. Check state attributes of
climate entity to find its id. 

```yaml
uponor:
    host: IP_ADDRESS_OF_UPONOR_DEVICE
    names:
      C1_T1: "Blue room"
      C1_T4: "Henry's room"
```

## Limitations

This integration supports heating only.

Uponor API does not support turn off action. When climate entity is turned off on Home Assistant,
the temperature is set to minimum (by default 5℃).

## Older module
In case you have older Uponor X-165 module visit: https://github.com/dave-code-ruiz/uhomeuponor

## Feedback

Your feedback, pull requests or any other contribution are welcome.
