import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPONOR_STATE_UPDATE

_LOGGER = logging.getLogger(__name__)  # Lägg till detta
async def async_setup_entry(hass, entry, async_add_entities):
    state_proxy = hass.data[DOMAIN]["state_proxy"]

    entities = []
    for thermostat in hass.data[DOMAIN]["thermostats"]:
        room_name = state_proxy.get_room_name(thermostat)
        _LOGGER.debug(f"Adding sensors for {room_name} (thermostat ID: {thermostat})")
        entities.append(UponorRoomCurrentTemperatureSensor(state_proxy, thermostat))
        
        if state_proxy.has_floor_temperature(thermostat):
            entities.append(UponorFloorTemperatureSensor(state_proxy, thermostat))
            _LOGGER.debug(f"Added floor sensor for: {room_name}")
        
        if state_proxy.has_humidity_sensor(thermostat):
            entities.append(UponorHumiditySensor(state_proxy, thermostat))
            _LOGGER.debug(f"Added humidity sensor for: {room_name}")
    
    _LOGGER.debug(f"Total number of sensors added: {len(entities)}")
    async_add_entities(entities, update_before_add=False)

class UponorFloorTemperatureSensor(SensorEntity):

    def __init__(self, state_proxy, thermostat):
        self._state_proxy = state_proxy
        self._thermostat = thermostat
        self._attr_name = f"{state_proxy.get_room_name(thermostat)} Floor Temperature"
        self._attr_unique_id = f"{state_proxy.get_thermostat_id(thermostat)}_floor_temp"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._state_proxy.get_thermostat_id(self._thermostat))},
            "name": self._state_proxy.get_room_name(self._thermostat),
            "manufacturer": "Uponor",
            "model": self._state_proxy.get_model(),
            "sw_version": self._state_proxy.get_version(self._thermostat)
        }

    @property
    def native_value(self):
        return self._state_proxy.get_floor_temperature(self._thermostat)

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
            )
        )
    @callback
    def _update_callback(self):
        """Update sensor state. when data updates"""
        _LOGGER.debug(f"Updating state for {self._attr_name} with ID {self._attr_unique_id}")
        self.async_write_ha_state()      

class UponorRoomCurrentTemperatureSensor(SensorEntity):

    def __init__(self, state_proxy, thermostat):
        self._state_proxy = state_proxy
        self._thermostat = thermostat
        self._attr_name = f"{state_proxy.get_room_name(thermostat)} Current Temperature"
        self._attr_unique_id = f"{state_proxy.get_thermostat_id(thermostat)}_current_temp"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._state_proxy.get_thermostat_id(self._thermostat))},
            "name": self._state_proxy.get_room_name(self._thermostat),
            "manufacturer": "Uponor",
            "model": self._state_proxy.get_model(),
            "sw_version": self._state_proxy.get_version(self._thermostat)
        }

    @property
    def native_value(self):
        return self._state_proxy.get_temperature(self._thermostat)

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
            )
        )
    @callback
    def _update_callback(self):
        """Update sensor state. when data updates"""
        _LOGGER.debug(f"Updating state for {self._attr_name} with ID {self._attr_unique_id}")
        self.async_write_ha_state()

class UponorHumiditySensor(SensorEntity):
    def __init__(self, state_proxy, thermostat):
        self._state_proxy = state_proxy
        self._thermostat = thermostat
        self._attr_name = f"{state_proxy.get_room_name(thermostat)} humidity"
        self._attr_unique_id = f"{state_proxy.get_thermostat_id(thermostat)}_rh"
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT 

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._state_proxy.get_thermostat_id(self._thermostat))},
            "name": self._state_proxy.get_room_name(self._thermostat),
            "manufacturer": "Uponor",
            "model": self._state_proxy.get_model(),
            "sw_version": self._state_proxy.get_version(self._thermostat)
        }

    @property
    def available(self):
        """Return True if the sensor is available."""
        return self._state_proxy.has_humidity_sensor(self._thermostat)

    @property
    def native_value(self):
        return self._state_proxy.get_humidity(self._thermostat)

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
            )
        )

    @callback
    def _update_callback(self):
        _LOGGER.debug(f"Updating state for {self._attr_name} with ID {self._attr_unique_id}")
        self.async_write_ha_state()