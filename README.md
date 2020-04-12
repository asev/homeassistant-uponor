# homeassistant-uponor

[![Buy me a smoothie](https://img.shields.io/badge/Buy%20me%20a-smoothie-blue?style=for-the-badge&logo=PAYPAL)](https://www.paypal.me/asev)

Custom component for Home Assistant to connect Uponor Smatrix Pulse X-265 heating system.

## Requirements

1. Uponor Smatrix Pulse controller X-265
2. Uponor Smatrix Pulse communication module R-208

## Installation

1. Startup and configure heating system on Uponor Smatrix mobile app. Make sure your can control heating via app. System has to be connected to local network and you should know it's IP address.
2. Copy the custom_components folder to your own Home Assistant /config folder.
3. Enable the component by adding the following in your `configuration.yml`:
```yaml
uponor:
    host: IP_ADDRESS_OF_UPONOR_DEVICE
```
4. Restart Home Assistant server
5. For every thermostat separete entity `climate.climate_tX` will be created. X - thermostat number.

## Configuration

- `names` (optional) custom name for every thermostat. By default room names configured in Uponor mobile app are used.

```yaml
uponor:
    host: IP_ADDRESS_OF_UPONOR_DEVICE
    names:
      t1: Living room
      t2: Bedroom
```

## Limitations

Uponor API does not support simple way to turn it off. So when heating is turned off on Home assistant, it sets temperature to 7℃.

## Feedback

Your feedback or pull requests or any other contribution is welcome. Please let me know how it works on other Helios models.
