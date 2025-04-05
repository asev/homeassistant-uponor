from datetime import timedelta

CONF_UNIQUE_ID = "unique_id"

DOMAIN = "uponor"

SIGNAL_UPONOR_STATE_UPDATE = "uponor_state_update"
SCAN_INTERVAL = timedelta(seconds=30)

STORAGE_KEY = "uponor_data"
STORAGE_VERSION = 1

DEVICE_MANUFACTURER = "Uponor"

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
DEFAULT_TEMP = 20
TEMP_CELSIUS = '°C'
