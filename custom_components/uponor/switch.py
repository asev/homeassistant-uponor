from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import (
    DOMAIN,
    SIGNAL_UPONOR_STATE_UPDATE
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    state_proxy = hass.data[DOMAIN]["state_proxy"]
    entities = [AwaySwitch(state_proxy)]
    if state_proxy.is_cool_available():
        entities.append(CoolSwitch(state_proxy))

    async_add_entities(entities)


class AwaySwitch(SwitchEntity):
    def __init__(self, state_proxy):
        self._state_proxy = state_proxy

    @property
    def name(self) -> str:
        return "Uponor Away"

    @property
    def icon(self):
        return "mdi:home-export-outline"

    @property
    def should_poll(self):
        return False

    @property
    def is_on(self):
        return self._state_proxy.is_away()

    async def async_turn_on(self, **kwargs):
        await self._state_proxy.async_set_away(True)

    async def async_turn_off(self, **kwargs):
        await self._state_proxy.async_set_away(False)

    async def async_added_to_hass(self):
        async_dispatcher_connect(
            self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
        )

    @callback
    def _update_callback(self):
        self.async_schedule_update_ha_state(True)


class CoolSwitch(SwitchEntity):
    def __init__(self, state_proxy):
        self._state_proxy = state_proxy

    @property
    def name(self) -> str:
        return "Uponor Cooling Mode"

    @property
    def icon(self):
        return "mdi:snowflake"

    @property
    def should_poll(self):
        return False

    @property
    def is_on(self):
        return self._state_proxy.is_cool_enabled()

    async def async_turn_on(self, **kwargs):
        await self._state_proxy.async_switch_to_cooling()

    async def async_turn_off(self, **kwargs):
        await self._state_proxy.async_switch_to_heating()

    async def async_added_to_hass(self):
        async_dispatcher_connect(
            self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
        )

    @callback
    def _update_callback(self):
        self.async_schedule_update_ha_state(True)
