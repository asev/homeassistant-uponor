from datetime import timedelta
import math
import ipaddress
import requests
import voluptuous as vol
import logging

from homeassistant.const import CONF_HOST, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
DOMAIN = "uponor"
DEFAULT_NAME = "Uponor"

SIGNAL_UPONOR_STATE_UPDATE = "uponor_state_update"
SCAN_INTERVAL = timedelta(seconds=30)

STATUS_OK = 'OK'
STATUS_ERROR_BATTERY = 'Battery error'
STATUS_ERROR_VALVE = 'Valve position error'
STATUS_ERROR_GENERAL = 'General system error'
STATUS_ERROR_AIR_SENSOR = 'Air sensor error'
STATUS_ERROR_EXT_SENSOR = 'External sensor error'
STATUS_ERROR_RH_SENSOR = 'Humidity sensor error'
STATUS_ERROR_RF_SENSOR = 'RF sensor error'
STATUS_ERROR_TAMPER = 'Tamper error'

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): vol.All(ipaddress.ip_address, cv.string),
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass, config):
    conf = config[DOMAIN]
    host = conf.get(CONF_HOST)
    name = conf.get(CONF_NAME)

    state_proxy = UponorStateProxy(hass, host)
    await state_proxy.async_update(0)
    thermostats = state_proxy.get_active_thermostats()

    hass.data[DOMAIN] = {"state_proxy": state_proxy, "name": name, "thermostats": thermostats}

    hass.async_create_task(async_load_platform(hass, "sensor", DOMAIN, {}, config))
    hass.async_create_task(async_load_platform(hass, "climate", DOMAIN, {}, config))

    async_track_time_interval(hass, state_proxy.async_update, SCAN_INTERVAL)

    return True

class UponorStateProxy:
    def __init__(self, hass, host):
        self._hass = hass
        self._host = host
        self._data = {}

    def get_active_thermostats(self):
        active = []
        for i in range(1, 13):
            var = 'C1_thermostat_' + str(i) + '_presence'
            if var in self._data and self._data[var] == "1":
                active.append(i)
        return active

    def is_heating_active(self, thermostat):
        var = 'C1_T' + str(thermostat) + '_stat_cb_actuator'
        if var in self._data:
            return self._data[var] == "1"

    def is_eco_mode_active(self, thermostat):
        var = 'C1_T' + str(thermostat) + '_stat_cb_eco_forced'
        var2 = 'C1_T' + str(thermostat) + '_stat_cb_comfort_eco_mode'
        if var in self._data or var2 in self._data :
            return self._data[var] == "1" or self._data[var2] == "1"

    def get_temperature(self, thermostat):
        var = 'C1_T' + str(thermostat) + '_room_temperature'
        if var in self._data:
            return round((int(self._data[var]) - 320) / 18,1)

    def get_humidity(self, thermostat):
        var = 'C1_T' + str(thermostat) + '_rh'
        if var in self._data:
            return int(self._data[var])

    def get_status(self, thermostat):
        var = 'C1_T' + str(thermostat) + '_stat_battery_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_BATTERY
        var = 'C1_T' + str(thermostat) + '_stat_valve_position_err"'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_VALVE
        var = 'C1_stat_general_system_alarm'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_GENERAL
        var = 'C1_T' + str(thermostat) + '_stat_air_sensor_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_AIR_SENSOR
        var = 'C1_T' + str(thermostat) + '_stat_external_sensor_err'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_EXT_SENSOR
        var = 'C1_T' + str(thermostat) + '_stat_rh_sensor_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_RH_SENSOR
        var = 'C1_T' + str(thermostat) + '_stat_rf_error'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_RF_SENSOR
        var = 'C1_T' + str(thermostat) + '_stat_tamper_alarm'
        if var in self._data and self._data[var] == "1":
            return STATUS_ERROR_TAMPER
        return STATUS_OK

    def get_setpoint(self, thermostat):
        var = 'C1_T' + str(thermostat) + '_setpoint'
        if var in self._data:
            return math.floor((int(self._data[var]) - 320) / 1.8) /10

    def set_setpoint(self, thermostat, temp):
        var = 'C1_T' + str(thermostat) + '_setpoint'
        setpoint = int(temp * 18 + 320)
        self.send(var, setpoint)
        self._data[var] = setpoint
        async_dispatcher_send(self._hass, SIGNAL_UPONOR_STATE_UPDATE)

    def send(self, var, value):
        url = "http://" + self._host + "/JNAP/"
        data = '{"vars": [{"waspVarName": "' + var + '","waspVarValue": "' + str(value) + '"}]}'
        r = requests.post(url=url, headers={"x-jnap-action": "http://phyn.com/jnap/uponorsky/SetAttributes"}, data=data)
        j = r.json()
        if 'results' in j and not j['results'] == 'OK':
            _LOGGER.error(j)

    async def async_update(self, event_time):
        url = "http://" + self._host + "/JNAP/"
        r = requests.post(url=url, headers={"x-jnap-action": "http://phyn.com/jnap/uponorsky/GetAttributes"}, data='{}')
        j = r.json()
        vars = {}
        for v in j['output']['vars']:
            vars[v['waspVarName']] = v['waspVarValue']
        self._data = vars

        async_dispatcher_send(self._hass, SIGNAL_UPONOR_STATE_UPDATE)

