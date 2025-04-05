import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature
)

from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    PRESET_AWAY,
    PRESET_ECO,
    ClimateEntityFeature
)

from .const import (
    SIGNAL_UPONOR_STATE_UPDATE,
    DEVICE_MANUFACTURER
)
from .helper import get_unique_id_from_config_entry

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    unique_id = get_unique_id_from_config_entry(entry)
    state_proxy = hass.data[unique_id]["state_proxy"]

    entities = []
    for thermostat in hass.data[unique_id]["thermostats"]:
        name = entry.data.get(thermostat.lower(), state_proxy.get_room_name(thermostat))
        entities.append(UponorClimate(unique_id, state_proxy, thermostat, name))
    
    if entities:
        async_add_entities(entities, update_before_add=False)

class UponorClimate(ClimateEntity):
    _enable_turn_on_off_backwards_compatibility = False
    def __init__(self, unique_instance_id, state_proxy, thermostat, name):
        self._unique_instance_id = unique_instance_id
        self._state_proxy = state_proxy
        self._thermostat = thermostat
        self._name = name
        temp = self._state_proxy.get_setpoint(self._thermostat)
        is_cool = self._state_proxy.is_cool_enabled()
        self._is_on = not ((is_cool and temp >= self.max_temp) or (not is_cool and temp <= self.min_temp))

    @property
    def device_info(self):
        return {
            "identifiers": {(self._unique_instance_id, self._state_proxy.get_thermostat_id(self._thermostat))},
            "name": self._name,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": self._state_proxy.get_model(),
            "sw_version": self._state_proxy.get_version(self._thermostat)
        }

    @property
    def name(self):
        return self._name

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
            )
        )

    @callback
    def _update_callback(self):
        temp = self._state_proxy.get_setpoint(self._thermostat)
        is_cool = self._state_proxy.is_cool_enabled()
        self._is_on = not ((is_cool and temp >= self.max_temp) or (not is_cool and temp <= self.min_temp))
        self.async_schedule_update_ha_state(True)

    @property
    def unique_id(self):
        return self._state_proxy.get_thermostat_id(self._thermostat)

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS
    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON

    @property
    def hvac_modes(self):
        return [HVACMode.COOL, HVACMode.OFF] if self._state_proxy.is_cool_enabled() else [HVACMode.HEAT, HVACMode.OFF]
    @property
    def preset_modes(self):
        return [PRESET_ECO, PRESET_AWAY]
    
    @property
    def current_humidity(self):
        humidity = self._state_proxy.get_humidity(self._thermostat)
        return humidity if humidity not in (None, 0) else None
    
    @property
    def current_temperature(self):
        return self._state_proxy.get_temperature(self._thermostat)
    
    @property
    def target_temperature(self):
        return self._state_proxy.get_setpoint(self._thermostat)

    @property
    def min_temp(self):
        return self._state_proxy.get_min_limit(self._thermostat)

    @property
    def max_temp(self):
        return self._state_proxy.get_max_limit(self._thermostat)

    @property
    def extra_state_attributes(self):
        return {
            'id': self._thermostat,
            'status': self._state_proxy.get_status(self._thermostat),
            'pulse_width_modulation': self._state_proxy.get_pwm(self._thermostat),
            'eco_setback': self._state_proxy.get_eco_setback(self._thermostat),
        }

    @property
    def preset_mode(self):
        if self._state_proxy.is_eco(self._thermostat):
            return PRESET_ECO
        if self._state_proxy.is_away():
            return PRESET_AWAY
        return None
    
    @property
    def hvac_mode(self):
        if not self._is_on:
            return HVACMode.OFF
        return HVACMode.COOL if self._state_proxy.is_cool_enabled() else HVACMode.HEAT

    @property
    def hvac_action(self):
        if not self._is_on:
            return HVACAction.OFF
        if self._state_proxy.is_active(self._thermostat):
            return HVACAction.COOLING if self._state_proxy.is_cool_enabled() else HVACAction.HEATING
        return HVACAction.IDLE

    async def async_turn_off(self):
        if self._is_on:
            await self._state_proxy.async_turn_off(self._thermostat)
            self._is_on = False

    async def async_turn_on(self):
        if not self._is_on:
            await self._state_proxy.async_turn_on(self._thermostat)
            self._is_on = True

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF and self._is_on:
            await self._state_proxy.async_turn_off(self._thermostat)
            self._is_on = False
        elif hvac_mode in [HVACMode.HEAT, HVACMode.COOL] and not self._is_on:
            await self._state_proxy.async_turn_on(self._thermostat)
            self._is_on = True

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None and self._is_on:
            await self._state_proxy.async_set_setpoint(self._thermostat, temp)
