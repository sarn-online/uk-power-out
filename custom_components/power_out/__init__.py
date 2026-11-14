"""Power Out reference integration."""
import json
import voluptuous as vol
from pathlib import Path
from functools import lru_cache
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.const import Platform
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv, entity_registry as er
from .const import DOMAIN, LETTERS
from .schedule import from_settings

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

def _reference_level(value):
    if type(value) is not int:
        raise vol.Invalid("Reference level must be an integer")
    return value

async def async_setup(hass, config):
    """Register the shared scenario action once for the integration."""
    async def set_scenario(call):
        entity_id = call.data["entity_id"]
        if call.context.user_id:
            user = await hass.auth.async_get_user(call.context.user_id)
            if user is None or not user.permissions.check_entity(entity_id, POLICY_CONTROL):
                raise Unauthorized(context=call.context, entity_id=entity_id)
        registered = er.async_get(hass).async_get(entity_id)
        entry = (hass.config_entries.async_get_entry(registered.config_entry_id)
                 if registered and registered.platform == DOMAIN and registered.config_entry_id else None)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError("Choose a Power Out reference entity")
        changes = {key: call.data[key] for key in ("rota", "level") if key in call.data}
        if not changes:
            raise ServiceValidationError("Choose a rota letter or reference level")
        options = {**entry.data, **entry.options, **changes}
        scenario = from_settings(options)
        # Tables are already cached by setup. A normal seven-day scenario is tiny.
        entry.runtime_data = (scenario, scenario.intervals(_tables()))
        hass.config_entries.async_update_entry(entry, options=options)
        async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_updated", entry.runtime_data)

    hass.services.async_register(DOMAIN, "set_scenario", set_scenario, schema=vol.Schema({
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("rota"): vol.In(LETTERS),
        vol.Optional("level"): vol.All(_reference_level, vol.Range(min=1, max=18)),
    }))
    return True

@lru_cache(maxsize=1)
def _tables():
    return json.loads(Path(__file__).with_name("schedules.json").read_text())

async def async_setup_entry(hass, entry):
    def load():
        tables = _tables()
        scenario = from_settings({**entry.data, **entry.options})
        return scenario, scenario.intervals(tables)
    entry.runtime_data = await hass.async_add_executor_job(load)
    entry.async_on_unload(entry.add_update_listener(_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def _reload(hass, entry):
    """Refresh existing entities; never unload platforms for a scenario edit."""
    scenario = from_settings({**entry.data, **entry.options})
    if entry.runtime_data[0] != scenario:
        entry.runtime_data = (scenario, scenario.intervals(_tables()))
        async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_updated", entry.runtime_data)

async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
