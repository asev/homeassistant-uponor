from .const import (
    DOMAIN
)


def get_unique_id_from(conf_name: str):

    raw_unique_id = DOMAIN + "_" + conf_name
    cleaned_unique_id = raw_unique_id.replace(" ", "_").lower()

    return cleaned_unique_id
