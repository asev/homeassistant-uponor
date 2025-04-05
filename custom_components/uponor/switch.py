from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.const import CONF_NAME
from .const import (
    SIGNAL_UPONOR_STATE_UPDATE,
    DEVICE_MANUFACTURER
)

from .helper import (
    get_unique_id_from_config_entry
)


async def async_setup_entry(hass, entry, async_add_entities):
    unique_id = get_unique_id_from_config_entry(entry)

    state_proxy = hass.data[unique_id]["state_proxy"]
    entities = [AwaySwitch(unique_id, state_proxy, entry.data[CONF_NAME])]

    if state_proxy.is_cool_available():
        entities.append(CoolSwitch(unique_id, state_proxy, entry.data[CONF_NAME]))

    async_add_entities(entities)


class AwaySwitch(SwitchEntity):
    def __init__(self, unique_instance_id, state_proxy, name):
        self._state_proxy = state_proxy
        self._name = name
        self._unique_instance_id = unique_instance_id

    @property
    def name(self) -> str:
        return self._name + " Away"

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
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._state_proxy.async_set_away(False)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
            )
        )

    @callback
    def _update_callback(self):
        self.async_write_ha_state()

    @property
    def unique_id(self):
        return f"{self._unique_instance_id}_away"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(self._unique_instance_id, "c")},
            name=self._name,
            manufacturer=DEVICE_MANUFACTURER,
            model=self._state_proxy.get_model(),
        )


class CoolSwitch(SwitchEntity):
    def __init__(self, unique_instance_id, state_proxy, name):
        self._state_proxy = state_proxy
        self._name = name
        self._unique_instance_id = unique_instance_id

    @property
    def name(self) -> str:
        return self._name + " Cooling Mode"

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
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._state_proxy.async_switch_to_heating()
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
            )
        )

    @callback
    def _update_callback(self):
        self.async_write_ha_state()

    @property
    def unique_id(self):
        return f"{self._unique_instance_id}_cool"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(self._unique_instance_id, "c")},
            name=self._name,
            manufacturer=DEVICE_MANUFACTURER,
            model=self._state_proxy.get_model(),
        )
