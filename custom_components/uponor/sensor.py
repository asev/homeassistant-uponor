from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.const import TEMP_CELSIUS

from . import (
    DOMAIN,
    SIGNAL_UPONOR_STATE_UPDATE
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    state_proxy = hass.data[DOMAIN]["state_proxy"]
    thermostats = hass.data[DOMAIN]["thermostats"]

    entities = []
    for thermostat in thermostats:
        if thermostat.lower() in hass.data[DOMAIN]["names"]:
            name = hass.data[DOMAIN]["names"][thermostat.lower()]
        else:
            name = state_proxy.get_room_name(thermostat)
        entities.append(UponorErrorSensor(state_proxy, thermostat, name))
    if entities:
        async_add_entities(entities, update_before_add=False)

class UponorErrorSensor(Entity):
    def __init__(self, state_proxy, thermostat, name):
        self._state_proxy = state_proxy
        self._thermostat = thermostat
        self._name = name + ' Status'

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state_proxy.get_status(self._thermostat)

    @property
    def should_poll(self):
        return False

    async def async_added_to_hass(self):
        async_dispatcher_connect(
            self.hass, SIGNAL_UPONOR_STATE_UPDATE, self._update_callback
        )

    @callback
    def _update_callback(self):
        self.async_schedule_update_ha_state(True)
