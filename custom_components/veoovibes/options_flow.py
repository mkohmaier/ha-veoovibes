from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

# Kein Import aus .const, um Importfehler zu vermeiden
CONF_SOURCE_MAP = "source_map"

EXAMPLE = (
    "sources:\n"
    "  - name: \"FM4\"\n"
    "    group: 1\n"
    "    prog: 3\n"
    "  - name: \"Lounge\"\n"
    "    group: 2\n"
    "    prog: 1\n"
)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options-Dialog: ein Textfeld für die globale Quellenliste (YAML/JSON)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_sources(user_input)

    async def async_step_sources(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_SOURCE_MAP, EXAMPLE)
        schema = vol.Schema({vol.Optional(CONF_SOURCE_MAP, default=current): str})
        return self.async_show_form(step_id="sources", data_schema=schema)

@callback
def async_get_options_flow(config_entry):
    return OptionsFlowHandler(config_entry)
