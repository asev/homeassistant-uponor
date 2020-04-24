import logging

from homeassistant.components.climate import ClimateDevice
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS

from . import (
    DOMAIN,
    SIGNAL_UPONOR_STATE_UPDATE
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    state_proxy = hass.data[DOMAIN]["state_proxy"]

    entities = []
    for thermostat in hass.data[DOMAIN]["thermostats"]:
        tid = "t" + str(thermostat)
        name = hass.data[DOMAIN]["names"][tid] if tid in hass.data[DOMAIN]["names"] else state_proxy.get_room_name(thermostat)
        entities.append(UponorClimate(state_proxy, str(thermostat), name))
    if entities:
        async_add_entities(entities, update_before_add=False)

class UponorClimate(ClimateDevice):

    def __init__(self, state_proxy, thermostat, name):
        self._state_proxy = state_proxy
        self._thermostat = thermostat
        self._name = name
        self._is_on = self._state_proxy.get_setpoint(self._thermostat) > self.min_temp
        self._last_temp = 20

    @property
    def name(self):
        return self._name

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        async_dispatcher_connect(
            self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
        )

    @callback
    def _update_callback(self):
        self._is_on = self._state_proxy.get_setpoint(self._thermostat) > self.min_temp
        self.async_schedule_update_ha_state(True)

    @property
    def supported_features(self):
        if self._is_on:
            return SUPPORT_TARGET_TEMPERATURE
        return 0

    @property
    def hvac_action(self):
        if not self._is_on:
            return CURRENT_HVAC_OFF
        if self._state_proxy.is_heating_active(self._thermostat):
            return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_IDLE

    @property
    def hvac_mode(self):
        if self._is_on:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_OFF and self._is_on:
            self._last_temp = self.target_temperature
            self._state_proxy.set_setpoint(self._thermostat, self.min_temp)
            self._is_on = False
        if hvac_mode == HVAC_MODE_HEAT and not self._is_on:
            self._state_proxy.set_setpoint(self._thermostat, self._last_temp)
            self._is_on = True

    @property
    def hvac_modes(self):
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._state_proxy.get_temperature(self._thermostat)

    @property
    def current_humidity(self):
        return self._state_proxy.get_humidity(self._thermostat)

    @property
    def min_temp(self):
        return self._state_proxy.get_min_limit(self._thermostat)

    @property
    def max_temp(self):
        return self._state_proxy.get_max_limit(self._thermostat)

    @property
    def target_temperature(self):
        return self._state_proxy.get_setpoint(self._thermostat)

    def set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None and self._is_on:
            self._state_proxy.set_setpoint(self._thermostat, temp)

