"""Exercise installed HA directly, without version-coupled pytest fixture internals."""
import asyncio
import json
from datetime import timedelta
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import homeassistant
from homeassistant import auth, bootstrap, config_entries, loader
from homeassistant.auth.auth_store import AuthStore
from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_READ_ONLY
from homeassistant.const import __version__
from homeassistant.core import Context, HomeAssistant, CoreState
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

async def main():
    with tempfile.TemporaryDirectory(prefix='powerout-ha-smoke-') as directory:
        hass=HomeAssistant(directory)
        auth_store=AuthStore(hass)
        hass.auth=auth.AuthManager(hass,auth_store,{},{})
        hass.config.skip_pip=True
        await hass.config.async_set_time_zone('Europe/London')
        loader.async_setup(hass)
        hass.config_entries=config_entries.ConfigEntries(hass,{})
        assert await bootstrap.async_load_base_functionality(hass)
        assert await async_setup_component(hass,'homeassistant',{})
        hass.set_state(CoreState.running)
        try:
            today=dt_util.now().date()
            data={'rota':'A','level':18,'plan_type':'vrdp_reference',
                  'start_date':(today-timedelta(days=1)).isoformat(),
                  'end_date':(today+timedelta(days=2)).isoformat()}
            result=await hass.config_entries.flow.async_init('power_out',context={'source':config_entries.SOURCE_USER})
            assert result['type']=='form',result
            result=await hass.config_entries.flow.async_configure(result['flow_id'],data)
            assert result['type']=='create_entry',result
            await hass.async_block_till_done()
            entry=result['result']
            states=[s for s in hass.states.async_all() if s.attributes.get('reference_only')]
            assert len(states)==4,states
            assert next(s for s in states if s.entity_id.startswith('binary_sensor.')).state=='on'
            assert next(s for s in states if 'supply' in s.entity_id).state=='Scheduled OFF'
            assert next(s for s in states if 'restoration' in s.entity_id).state=='unknown'
            options=await hass.config_entries.options.async_init(entry.entry_id)
            changed={**data,'rota':'N','level':1}
            options=await hass.config_entries.options.async_configure(options['flow_id'],changed)
            assert options['type']=='create_entry'
            await hass.async_block_till_done()
            assert entry.options==changed
            assert entry.runtime_data[0].rota=='N'
            interruptions=[]
            def observe(event):
                entity_id=event.data['entity_id']
                new=event.data.get('new_state')
                if 'power_out' in entity_id and (new is None or new.state=='unavailable'):interruptions.append(entity_id)
            unsubscribe=hass.bus.async_listen('state_changed',observe)
            before_states={s.entity_id:s.last_changed for s in hass.states.async_all() if s.attributes.get('reference_only')}
            original_runtime=entry.runtime_data
            supply=next(s.entity_id for s in hass.states.async_all() if 'supply' in s.entity_id and s.attributes.get('reference_only'))
            await hass.services.async_call('power_out','set_scenario',{'entity_id':supply,'rota':'P'},blocking=True)
            await hass.async_block_till_done()
            assert entry.options['rota']=='P' and entry.options['level']==1
            assert entry.state.value=='loaded'
            assert all(hass.states.get(entity_id).state!='unavailable' for entity_id in before_states)
            assert entry.options['start_date']==data['start_date'] and entry.options['end_date']==data['end_date']
            await hass.services.async_call('power_out','set_scenario',{'entity_id':supply,'level':5},blocking=True)
            await hass.async_block_till_done()
            assert entry.options['rota']=='P' and entry.runtime_data[0].level==5
            assert not interruptions,interruptions
            assert all(s.attributes['rota']=='P' and s.attributes['level']==5 for s in hass.states.async_all() if s.attributes.get('reference_only'))
            unsubscribe()
            print('PASS: all four entities update in place with no unavailable or removal events')
            for payload in ({'rota':'F'},{'level':19},{'level':True},{'level':1.5},{'entity_id':'sensor.unrelated','level':1},{}):
                try:
                    await hass.services.async_call('power_out','set_scenario',{'entity_id':supply,**payload},blocking=True)
                except Exception as error:
                    from homeassistant.exceptions import ServiceValidationError
                    import voluptuous as vol
                    assert isinstance(error,(ServiceValidationError,vol.Invalid)),error
                else:
                    raise AssertionError(f'Invalid action accepted: {payload}')
            await auth_store.async_load()
            admin=await hass.auth.async_create_user('Admin test',group_ids=[GROUP_ID_ADMIN])
            reader=await hass.auth.async_create_user('Read-only test',group_ids=[GROUP_ID_READ_ONLY])
            try:
                await hass.services.async_call('power_out','set_scenario',{'entity_id':supply,'level':6},blocking=True,context=Context(user_id=reader.id))
            except Exception as error:
                from homeassistant.exceptions import Unauthorized
                assert isinstance(error,Unauthorized),error
            else:
                raise AssertionError('Read-only user was allowed to change shared settings')
            await hass.services.async_call('power_out','set_scenario',{'entity_id':supply,'level':5},blocking=True,context=Context(user_id=admin.id))
            await hass.async_block_till_done()
            assert entry.options['level']==5
            print('PASS: authenticated admin can save and read-only users cannot change the shared scenario')
            changed.update(rota='P',level=5)
            print('PASS: shared dropdown actions change only their field, preserve dates and reject invalid targets/values')
            assert await hass.config_entries.async_unload(entry.entry_id)
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.runtime_data[0].rota=='P'
            assert len([s for s in hass.states.async_all() if s.attributes.get('reference_only')])==4
            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            print(f'PASS: Home Assistant {__version__}: UI flow, four entities, level 18, options reload, persistent entry reuse and unload')
        finally:
            await hass.async_stop(force=True)
        stored=json.loads((Path(directory)/'.storage/core.config_entries').read_text())
        saved=next(item for item in stored['data']['entries'] if item['domain']=='power_out')
        assert saved['options']==changed
        assert saved['data']==data
        print('PASS: original scenario and changed options persisted to Home Assistant storage')

if __name__=='__main__': asyncio.run(main())
