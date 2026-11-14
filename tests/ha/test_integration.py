"""Run against real Home Assistant via pytest-homeassistant-custom-component."""
from datetime import timedelta
import pytest
from homeassistant import config_entries
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures('enable_custom_integrations')

def settings():
    today=dt_util.now().date()
    return {'rota':'A','level':18,'plan_type':'vrdp_reference',
            'start_date':(today-timedelta(days=1)).isoformat(),
            'end_date':(today+timedelta(days=2)).isoformat()}

@pytest.mark.asyncio
async def test_user_flow(hass):
    result=await hass.config_entries.flow.async_init('power_out', context={'source':config_entries.SOURCE_USER})
    assert result['type']=='form'
    result=await hass.config_entries.flow.async_configure(result['flow_id'],settings())
    assert result['type']=='create_entry'
    await hass.async_block_till_done()
    assert result['data']==settings()

@pytest.mark.asyncio
async def test_setup_options_reload_and_unload(hass):
    entry=MockConfigEntry(domain='power_out',data=settings(),title='Reference')
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entities=[state for state in hass.states.async_all() if state.attributes.get('reference_only')]
    assert len(entities)==4
    assert next(s for s in entities if s.entity_id.startswith('binary_sensor.')).state=='on'
    assert next(s for s in entities if 'supply' in s.entity_id).state=='Scheduled OFF'
    result=await hass.config_entries.options.async_init(entry.entry_id)
    changed={**settings(),'rota':'N','level':1}
    result=await hass.config_entries.options.async_configure(result['flow_id'],changed)
    assert result['type']=='create_entry'
    await hass.async_block_till_done()
    assert entry.options==changed
    assert entry.runtime_data[0].rota=='N'
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

@pytest.mark.asyncio
async def test_invalid_dates(hass):
    result=await hass.config_entries.flow.async_init('power_out',context={'source':config_entries.SOURCE_USER})
    data={**settings(),'start_date':'2026-11-15','end_date':'2026-11-14'}
    result=await hass.config_entries.flow.async_configure(result['flow_id'],data)
    assert result['errors']=={'base':'invalid_scenario'}

@pytest.mark.asyncio
async def test_exact_transitions_and_expiry(hass, freezer):
    from datetime import datetime, timezone
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    freezer.move_to('2026-11-09T00:29:59Z')
    data={'rota':'A','level':1,'plan_type':'vrdp_reference',
          'start_date':'2026-11-09','end_date':'2026-11-09'}
    entry=MockConfigEntry(domain='power_out',data=data,title='Reference')
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    def restriction():
        return next(s for s in hass.states.async_all('binary_sensor') if s.attributes.get('reference_only'))
    assert restriction().state=='unknown'
    for instant,expected in [('2026-11-09T00:30:00+00:00','on'),
                             ('2026-11-09T03:30:00+00:00','off'),
                             ('2026-11-10T00:30:00+00:00','unknown')]:
        target=datetime.fromisoformat(instant)
        freezer.move_to(target)
        async_fire_time_changed(hass,target)
        await hass.async_block_till_done()
        assert restriction().state==expected
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
