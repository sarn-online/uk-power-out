"""Persistent UI configuration of an explicitly hypothetical scenario."""
from datetime import timedelta
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util
from .const import DOMAIN, LETTERS, PLAN
from .schedule import from_settings

def schema(defaults):
    today = dt_util.now().date()
    defaults = {"rota": "A", "level": 1, "plan_type": PLAN,
                "start_date": today.isoformat(), "end_date": (today+timedelta(days=6)).isoformat(), **defaults}
    return vol.Schema({
        vol.Required("rota", default=defaults["rota"]): selector.SelectSelector(
            selector.SelectSelectorConfig(options=list(LETTERS))),
        vol.Required("level", default=defaults["level"]): vol.All(vol.Coerce(int), vol.Range(min=1,max=18)),
        vol.Required("plan_type", default=defaults["plan_type"]): selector.SelectSelector(
            selector.SelectSelectorConfig(options=[{"value": PLAN, "label": "Variable Rota — Annex 2 reference only"}])),
        vol.Required("start_date", default=defaults["start_date"]): selector.DateSelector(),
        vol.Required("end_date", default=defaults["end_date"]): selector.DateSelector(),
    })

class PowerOutConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                from_settings(user_input)
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_scenario"
            else:
                return self.async_create_entry(title=f"Power Out {user_input['rota']} reference", data=user_input)
        return self.async_show_form(step_id="user", data_schema=schema(user_input or {}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PowerOutOptionsFlow()

class PowerOutOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                from_settings(user_input)
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_scenario"
            else:
                return self.async_create_entry(title="", data=user_input)
        defaults = {**self.config_entry.data, **self.config_entry.options, **(user_input or {})}
        return self.async_show_form(step_id="init", data_schema=schema(defaults), errors=errors)
