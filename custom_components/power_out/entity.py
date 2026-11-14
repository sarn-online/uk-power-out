"""Shared reference metadata and exact transition updates."""
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

class PowerOutEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry, key, name):
        self._entry_id = entry.entry_id
        self.scenario, self.intervals = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._cancel = None

    @property
    def extra_state_attributes(self):
        s = self.scenario
        return {"reference_only": True, "actual_activation_known": False,
                "plan_type": s.plan_type, "rota": s.rota, "level": s.level,
                "start_date": s.start_date.isoformat(), "end_date": s.end_date.isoformat(),
                "valid_from": s.start.isoformat(), "valid_until": s.end.isoformat(),
                "source": "ESEC April 2026 Annex 2 PDF", "time_zone": "Europe/London"}

    def values(self):
        return self.scenario.evaluate(dt_util.utcnow(), self.intervals)

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(
            self.hass, f"{DOMAIN}_{self._entry_id}_updated", self._scenario_updated))
        self._schedule()

    @callback
    def _scenario_updated(self, runtime_data):
        self.scenario, self.intervals = runtime_data
        self._schedule()
        self.async_write_ha_state()

    @callback
    def _schedule(self, now=None):
        if self._cancel:
            self._cancel()
            self._cancel = None
        now = dt_util.utcnow()
        points = [self.scenario.start, self.scenario.end]
        points.extend(t for interval in self.intervals for t in interval)
        future = [t for t in points if t > now]
        if future:
            self._cancel = async_track_point_in_utc_time(self.hass, self._changed, min(future))

    @callback
    def _changed(self, now):
        self.async_write_ha_state()
        self._schedule()

    async def async_will_remove_from_hass(self):
        if self._cancel:
            self._cancel()
