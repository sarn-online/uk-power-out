"""ON means a reference restriction is scheduled, not electricity ON."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from .entity import PowerOutEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([Restriction(entry)])

class Restriction(PowerOutEntity, BinarySensorEntity):
    _attr_icon = "mdi:transmission-tower-off"

    def __init__(self, entry):
        super().__init__(entry, "restriction", "Power Out reference restriction")

    @property
    def is_on(self):
        return self.values()[0]
