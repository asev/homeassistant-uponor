from datetime import timedelta
import math
import ipaddress
import requests
import voluptuous as vol
import logging

from homeassistant.const import CONF_HOST
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from UponorJnap import UponorJnap

_LOGGER = logging.getLogger(__name__)
DOMAIN = "uponor"
CONF_NAMES = "names"

SIGNAL_UPONOR_STATE_UPDATE = "uponor_state_update"
SCAN_INTERVAL = timedelta(seconds=30)

STORAGE_KEY = "uponor_data"
STORAGE_VERSION = 1

STATUS_OK = 'OK'
STATUS_ERROR_BATTERY = 'Battery error'
STATUS_ERROR_VALVE = 'Valve position error'
STATUS_ERROR_GENERAL = 'General system error'
STATUS_ERROR_AIR_SENSOR = 'Air sensor error'
STATUS_ERROR_EXT_SENSOR = 'External sensor error'
STATUS_ERROR_RH_SENSOR = 'Humidity sensor error'
STATUS_ERROR_RF_SENSOR = 'RF sensor error'
STATUS_ERROR_TAMPER = 'Tamper error'
STATUS_ERROR_TOO_HIGH_TEMP = 'API error'
TOO_HIGH_TEMP_LIMIT = 4508
TOO_LOW_HUMIDITY_LIMIT = 0

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): vol.All(ipaddress.ip_address, cv.string),
                vol.Optional(CONF_NAMES, default={}): vol.All()
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass, config):
    conf = config[DOMAIN]
    host = conf.get(CONF_HOST)
    names = dict((k.lower(), v) for k,v in conf.get(CONF_NAMES).items())
    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)

    state_proxy = await hass.async_add_executor_job(lambda: UponorStateProxy(hass, host, store))
    await state_proxy.async_update(0)
    thermostats = state_proxy.get_active_thermostats()

    hass.data[DOMAIN] = {
        "state_proxy": state_proxy,
        "names": names,
        "thermostats": thermostats
    }

    hass.async_create_task(async_load_platform(hass, "climate", DOMAIN, {}, config))

    async_track_time_interval(hass, state_proxy.async_update, SCAN_INTERVAL)

    return True

class UponorStateProxy:
    def __init__(self, hass, host, store):
        self._hass = hass
        self._client = UponorJnap(host)
        self._store = store
        self._data = {}
        self._storage_data = {}

    def get_active_thermostats(self):
        active = []
        for c in range(1, 5):
            var = 'sys_controller_' + str(c) + '_presence'
            if var in self._data and self._data[var] != "1":
                continue
            for i in range(1, 13):
                var = 'C' + str(c) + '_thermostat_' + str(i) + '_presence'
                if var in self._data and self._data[var] == "1":
                    active.append('C' + str(c) + '_T' + str(i))
        return active

    def is_heating_active(self, thermostat):
        var = thermostat + '_stat_cb_actuator'
        if var in self._data:
            return self._data[var] == "1"

    def get_temperature(self, thermostat):
        var = thermostat + '_room_temperature'
        if var in self._data and int(self._data[var]) <= TOO_HIGH_TEMP_LIMIT:
            return round((int(self._data[var]) - 320) / 18,1)

    def get_min_limit(self, thermostat):
        var = thermostat + '_minimum_setpoint'
        if var in self._data:
            return round((int(self._data[var]) - 320) / 18,1)

    def get_max_limit(self, thermostat):
        var = thermostat + '_maximum_setpoint'
        if var in self._data:
            return round((int(self._data[var]) - 320) / 18,1)

    def get_humidity(self, thermostat):
        var = thermostat + '_rh'
        if var in self._data and int(self._data[var]) >= TOO_LOW_HUMIDITY_LIMIT:
            return int(self._data[var])

    def get_room_name(self, thermostat):
        var = 'cust_' + thermostat + '_name'
        if var in self._data:
            return self._data[var]
        
        return thermostat

    def get_status(self, thermostat):
        var = thermostat + '_stat_battery_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_BATTERY
        var = thermostat + '_stat_valve_position_err"'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_VALVE
        var = thermostat[0:3] + 'stat_general_system_alarm'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_GENERAL
        var = thermostat + '_stat_air_sensor_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_AIR_SENSOR
        var = thermostat + '_stat_external_sensor_err'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_EXT_SENSOR
        var = thermostat + '_stat_rh_sensor_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_RH_SENSOR
        var = thermostat + '_stat_rf_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_RF_SENSOR
        var = thermostat + '_stat_tamper_alarm'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_TAMPER
        var = thermostat + '_room_temperature'
        if var in self._data and int(self._data[var]) > TOO_HIGH_TEMP_LIMIT:
            return STATUS_ERROR_TOO_HIGH_TEMP
        return STATUS_OK

    def get_setpoint(self, thermostat):
        var = thermostat + '_setpoint'
        if var in self._data:
            return math.floor((int(self._data[var]) - 320) / 1.8) /10

    def set_setpoint(self, thermostat, temp):
        var = thermostat + '_setpoint'
        setpoint = int(temp * 18 + 320)
        self._client.send_data({var: setpoint})
        self._data[var] = setpoint
        async_dispatcher_send(self._hass, SIGNAL_UPONOR_STATE_UPDATE)

    async def async_turn_on(self, thermostat):
        data = await self._store.async_load()
        self._storage_data = {} if data is None else data
        last_temp = self._storage_data[thermostat] if thermostat in self._storage_data else 20
        self.set_setpoint(thermostat, last_temp)

    async def async_turn_off(self, thermostat):
        data = await self._store.async_load()
        self._storage_data = {} if data is None else data
        self._storage_data[thermostat] = self.get_setpoint(thermostat)
        await self._store.async_save(self._storage_data)
        self.set_setpoint(thermostat, self.get_min_limit(thermostat))

    async def async_update(self, event_time):
        self._data = await self._hass.async_add_executor_job(lambda: self._client.get_data())
        async_dispatcher_send(self._hass, SIGNAL_UPONOR_STATE_UPDATE)
