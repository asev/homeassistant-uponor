import logging

from homeassistant.components.climate import ClimateEntity

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
    DOMAIN,
    DEVICE_MANUFACTURER
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    state_proxy = hass.data[DOMAIN]["state_proxy"]

    entities = []
    for thermostat in hass.data[DOMAIN]["thermostats"]:
        if thermostat.lower() in entry.data:
            name = entry.data[thermostat.lower()]
        else:
            name = state_proxy.get_room_name(thermostat)
        entities.append(UponorClimate(state_proxy, thermostat, name))
    if entities:
        async_add_entities(entities, update_before_add=False)


class UponorClimate(ClimateEntity):

    _enable_turn_on_off_backwards_compatibility = False
    
    def __init__(self, state_proxy, thermostat, name):
        self._state_proxy = state_proxy
        self._thermostat = thermostat
        self._name = name
        temp = self._state_proxy.get_setpoint(self._thermostat)
        is_cool = self._state_proxy.is_cool_enabled()
        self._is_on = not ((is_cool and temp >= self.max_temp) or (not is_cool and temp <= self.min_temp))

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._state_proxy.get_thermostat_id(self._thermostat))},
            "name": self._name,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": self._state_proxy.get_model(),
            "sw_version": self._state_proxy.get_version(self._thermostat)
        }

    @property
    def name(self):
        return self._name
    
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
        if self._state_proxy.is_cool_enabled():
            return [HVACMode.COOL, HVACMode.OFF]
        return [HVACMode.HEAT, HVACMode.OFF]
    
    @property
    def preset_modes(self):
        return [self.preset_mode] if self.preset_mode is not None else []
    
    @property
    def current_humidity(self):
        return self._state_proxy.get_humidity(self._thermostat)
    
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
        if self._state_proxy.is_cool_enabled():
            return HVACMode.COOL
        return HVACMode.HEAT

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

    # ** Actions **
    async def async_update(self):
        # Update uponor (to get HC mode) and thermostat
        try:
            ### se ha elimininado el 0 del update
            await self._state_proxy.async_update()
            temp = self._state_proxy.get_setpoint(self._thermostat)
            is_cool = self._state_proxy.is_cool_enabled()
            self._is_on = not ((is_cool and temp >= self.max_temp) or (not is_cool and temp <= self.min_temp))

        except Exception as ex:
            _LOGGER.error("Uponor thermostat was unable to update: %s", ex)

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF and self._is_on:
            await self._state_proxy.async_turn_off(self._thermostat)
            self._is_on = False
        if (hvac_mode == HVACMode.HEAT or hvac_mode == HVACMode.COOL) and not self._is_on:
            await self._state_proxy.async_turn_on(self._thermostat)
            self._is_on = True
        
        # if (hvac_mode == HVACMode.HEAT):
        #     await self._state_proxy.async_switch_to_heating()
        # if (hvac_mode == HVACMode.COOL):
        #     await self._state_proxy.async_switch_to_cooling()
        

    async def async_set_temperature(self, **kwargs):
        if kwargs.get(ATTR_TEMPERATURE) is None:
            return
        await self._state_proxy.set_setpoint(self._thermostat, kwargs.get(ATTR_TEMPERATURE))


