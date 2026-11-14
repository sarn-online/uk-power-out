"""Reference status and upcoming timestamps."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from .entity import PowerOutEntity

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ReferenceSensor(entry, key, name, index) for key,name,index in (
        ("status", "Power Out reference supply", 0),
        ("next_restriction", "Power Out next reference restriction", 1),
        ("next_restoration", "Power Out next reference restoration", 2))])

class ReferenceSensor(PowerOutEntity, SensorEntity):
    def __init__(self, entry, key, name, index):
        super().__init__(entry, key, name)
        self.index = index
        if index:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        value = self.values()[self.index]
        if self.index:
            return value
        return None if value is None else "Scheduled OFF" if value else "Scheduled ON"
