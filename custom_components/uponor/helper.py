from .const import (
    DOMAIN,
    CONF_UNIQUE_ID
)

from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    CONF_NAME
)


def create_unique_id_from_user_input(user_input):
    if CONF_UNIQUE_ID not in user_input and user_input[CONF_UNIQUE_ID] != "":
        return user_input[CONF_UNIQUE_ID]

    return None


def generate_unique_id_from_user_input_conf_name(user_input):
    conf_name = user_input[CONF_NAME]
    raw_unique_id = DOMAIN + "_" + conf_name
    cleaned_unique_id = raw_unique_id.replace(" ", "_").lower()
    return cleaned_unique_id


def get_unique_id_from_config_entry(config_entry : ConfigEntry):
    return config_entry.unique_id
