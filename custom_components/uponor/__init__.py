import math
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from homeassistant.const import CONF_HOST
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from UponorJnap import UponorJnap
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    SIGNAL_UPONOR_STATE_UPDATE,
    SCAN_INTERVAL,
    STORAGE_KEY,
    STORAGE_VERSION,
    STATUS_OK,
    STATUS_ERROR_BATTERY,
    STATUS_ERROR_VALVE,
    STATUS_ERROR_GENERAL,
    STATUS_ERROR_AIR_SENSOR,
    STATUS_ERROR_EXT_SENSOR,
    STATUS_ERROR_RH_SENSOR,
    STATUS_ERROR_RF_SENSOR,
    STATUS_ERROR_TAMPER,
    STATUS_ERROR_TOO_HIGH_TEMP,
    TOO_HIGH_TEMP_LIMIT,
    TOO_LOW_HUMIDITY_LIMIT,
    DEFAULT_TEMP
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = config.get(DOMAIN) or {}
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    host = config_entry.data[CONF_HOST]
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    state_proxy = await hass.async_add_executor_job(lambda: UponorStateProxy(hass, host, store))
    await state_proxy.async_update()
    thermostats = state_proxy.get_active_thermostats()

    hass.data[DOMAIN] = {
        "state_proxy": state_proxy,
        "thermostats": thermostats
    }

    def handle_set_variable(call):
        var_name = call.data.get('var_name')
        var_value = call.data.get('var_value')
        hass.data[DOMAIN]['state_proxy'].set_variable(var_name, var_value)

    hass.services.async_register(DOMAIN, "set_variable", handle_set_variable)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    async_track_time_interval(hass, state_proxy.async_update, SCAN_INTERVAL)

    config_entry.async_on_unload(config_entry.add_update_listener(async_update_options))

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug("Update setup entry: %s, data: %s, options: %s", entry.entry_id, entry.data, entry.options)
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading setup entry: %s, data: %s, options: %s", config_entry.entry_id, config_entry.data, config_entry.options)
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, [Platform.SWITCH, Platform.CLIMATE])
    return unload_ok

class UponorStateProxy:
    def __init__(self, hass, host, store):
        self._hass = hass
        self._client = UponorJnap(host)
        self._store = store
        self._data = {}
        self._storage_data = {}
        self.next_sp_from_dt = None

    # Thermostats config

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

    def get_room_name(self, thermostat):
        var = 'cust_' + thermostat + '_name'
        if var in self._data:
            return self._data[var]
        return thermostat

    def get_thermostat_id(self, thermostat):
        var = thermostat.replace('T', 'thermostat') + '_id'
        if var in self._data:
            return self._data[var]

    def get_model(self):
        var = 'cust_SW_version_update'
        if var in self._data:
            return self._data[var].split('_')[0]
        return '-'

    def get_version(self, thermostat):
        var = thermostat[0:3] + 'sw_version'
        if var in self._data:
            return self._data[var].split('_')[0]

    # Temperatures & humidity

    def get_temperature(self, thermostat):
        var = thermostat + '_room_temperature'
        if var in self._data and int(self._data[var]) <= TOO_HIGH_TEMP_LIMIT:
            return round((int(self._data[var]) - 320) / 18, 1)

    def get_min_limit(self, thermostat):
        var = thermostat + '_minimum_setpoint'
        if var in self._data:
            return round((int(self._data[var]) - 320) / 18, 1)

    def get_max_limit(self, thermostat):
        var = thermostat + '_maximum_setpoint'
        if var in self._data:
            return round((int(self._data[var]) - 320) / 18, 1)

    def get_humidity(self, thermostat):
        var = thermostat + '_rh'
        if var in self._data and int(self._data[var]) >= TOO_LOW_HUMIDITY_LIMIT:
            return int(self._data[var])

    # Temperature setpoint

    def get_setpoint(self, thermostat):
        var = thermostat + '_setpoint'
        if var in self._data:
            temp = math.floor((int(self._data[var]) - 320) / 1.8) / 10
            return math.floor((int(self._data[var]) - self.get_active_setback(thermostat, temp) - 320) / 1.8) / 10

    def get_active_setback(self, thermostat, temp):
        if temp == self.get_min_limit(thermostat) or temp == self.get_max_limit(thermostat):
            return 0

        cool_setback = 0
        var_cool_setback = 'sys_heat_cool_offset'
        if var_cool_setback in self._data and self.is_cool_enabled():
            cool_setback = int(self._data[var_cool_setback]) * -1

        eco_setback = 0
        var_eco_setback = thermostat + '_eco_offset'
        mode = -1 if self.is_cool_enabled() else 1
        if var_eco_setback in self._data and (self.is_eco(thermostat) or self.is_away()):
            eco_setback = int(self._data[var_eco_setback]) * mode

        return cool_setback + eco_setback

    # State

    def is_active(self, thermostat):
        var = thermostat + '_stat_cb_actuator'
        if var in self._data:
            return self._data[var] == "1"

    def get_pwm(self, thermostat):
        var = thermostat + '_ufh_pwm_output'
        if var in self._data:
            return int(self._data[var])

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

    # HVAC modes

    async def async_switch_to_cooling(self):
        for thermostat in self._hass.data[DOMAIN]['thermostats']:
            if self.get_setpoint(thermostat) == self.get_min_limit(thermostat):
                await self.set_setpoint(thermostat, self.get_max_limit(thermostat))
        
        await self._hass.async_add_executor_job(lambda: self._client.send_data({'sys_heat_cool_mode': '1'}))
        self._data['sys_heat_cool_mode'] = '1'
        self._hass.async_create_task(self.call_state_update())

    async def async_switch_to_heating(self):
        for thermostat in self._hass.data[DOMAIN]['thermostats']:
            if self.get_setpoint(thermostat) == self.get_max_limit(thermostat):
                await self.set_setpoint(thermostat, self.get_min_limit(thermostat))

        await self._hass.async_add_executor_job(lambda: self._client.send_data({'sys_heat_cool_mode': '0'}))
        self._data['sys_heat_cool_mode'] = '0'
        self._hass.async_create_task(self.call_state_update())

    async def async_turn_on(self, thermostat):
        data = await self._store.async_load()
        self._storage_data = {} if data is None else data
        last_temp = self._storage_data[thermostat] if thermostat in self._storage_data else DEFAULT_TEMP
        await self.set_setpoint(thermostat, last_temp)

    async def async_turn_off(self, thermostat):
        data = await self._store.async_load()
        self._storage_data = {} if data is None else data
        self._storage_data[thermostat] = self.get_setpoint(thermostat)
        await self._store.async_save(self._storage_data)
        off_temp = self.get_max_limit(thermostat) if self.is_cool_enabled() else self.get_min_limit(thermostat)
        await self.set_setpoint(thermostat, off_temp)

    # Cooling

    def is_cool_available(self):
        var = 'sys_cooling_available'
        if var in self._data:
            return self._data[var] == "1"

    def is_cool_enabled(self):
        var = 'sys_heat_cool_mode'
        if var in self._data:
            return self._data[var] == "1"

    # Away & Eco

    def is_away(self):
        var = 'sys_forced_eco_mode'
        return var in self._data and self._data[var] == "1"

    async def async_set_away(self, is_away):
        var = 'sys_forced_eco_mode'
        data = "1" if is_away else "0"
        await self._hass.async_add_executor_job(lambda: self._client.send_data({var: data}))
        self._data[var] = data
        self._hass.async_create_task(self.call_state_update())

    def is_eco(self, thermostat):
        if self.get_eco_setback(thermostat) == 0:
            return False
        var = thermostat + '_stat_cb_comfort_eco_mode'
        var_temp = 'cust_Temporary_ECO_Activation'
        return (var in self._data and self._data[var] == "1") or (
                    var_temp in self._data and self._data[var_temp] == "1")

    def get_eco_setback(self, thermostat):
        var = thermostat + '_eco_offset'
        if var in self._data:
            return round(int(self._data[var]) / 18, 1)
        
    def get_last_update(self):
        return self.next_sp_from_dt
    
    def call_state_update(self):
        async_dispatcher_send(self._hass, SIGNAL_UPONOR_STATE_UPDATE)

    # Rest
    async def async_update(self,_=None):
        try:
            self.next_sp_from_dt = dt_util.now()
            self._data = await self._hass.async_add_executor_job(lambda: self._client.get_data())
            self._hass.async_create_task(self.call_state_update())
        except Exception as ex:
            _LOGGER.error("Uponor thermostat was unable to update: %s", ex)
        
    def set_variable(self, var_name, var_value):
        _LOGGER.debug("Called set variable: name: %s, value: %s, data: %s", var_name, var_value, self._data)
        self._client.send_data({var_name: var_value})
        self._data[var_name] = var_value
        self._hass.async_create_task(self.call_state_update())

    async def set_setpoint(self, thermostat, temp):
        var = thermostat + '_setpoint'
        setpoint = int(temp * 18 + self.get_active_setback(thermostat, temp) + 320)
        await self._hass.async_add_executor_job(lambda: self._client.send_data({var: setpoint}))
        self._data[var] = setpoint
        self._hass.async_create_task(self.call_state_update())
