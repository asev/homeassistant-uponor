from homeassistant.components.switch import SwitchEntity

from homeassistant.const import CONF_NAME
from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER
)


async def async_setup_entry(hass, entry, async_add_entities):
    state_proxy = hass.data[DOMAIN]["state_proxy"]
    entities = [AwaySwitch(state_proxy, entry.data[CONF_NAME])]

    if state_proxy.is_cool_available():
        entities.append(CoolSwitch(state_proxy, entry.data[CONF_NAME]))

    async_add_entities(entities)


class AwaySwitch(SwitchEntity):
    def __init__(self, state_proxy, name):
        self._state_proxy = state_proxy
        self._name = name

    @property
    def name(self) -> str:
        return self._name + " Away"

    @property
    def icon(self):
        return "mdi:home-export-outline"

    # @property
    # def should_poll(self):
    #     return False

    @property
    def is_on(self):
        return self._state_proxy.is_away()

    async def async_turn_on(self, **kwargs):
        await self._state_proxy.async_set_away(True)

    async def async_turn_off(self, **kwargs):
        await self._state_proxy.async_set_away(False)

    async def async_update(self):
        await self._state_proxy.async_update()

    @property
    def unique_id(self):
        return self.name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "c")},
            "name": self._name,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": self._state_proxy.get_model(),
        }


class CoolSwitch(SwitchEntity):
    def __init__(self, state_proxy, name):
        self._state_proxy = state_proxy
        self._name = name

    @property
    def name(self) -> str:
        return self._name + " Cooling Mode"

    @property
    def icon(self):
        return "mdi:snowflake"

    # @property
    # def should_poll(self):
    #     return False

    @property
    def is_on(self):
        return self._state_proxy.is_cool_enabled()

    async def async_turn_on(self, **kwargs):
        await self._state_proxy.async_switch_to_cooling()

    async def async_turn_off(self, **kwargs):
        await self._state_proxy.async_switch_to_heating()
        
    async def async_update(self):
        await self._state_proxy.async_update()

    @property
    def unique_id(self):
        return self.name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, "c")},
            "name": self._name,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": self._state_proxy.get_model(),
        }
