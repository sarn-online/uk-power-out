"""Offline HACS layout checks; remote HACS/brands validation remains separate."""
import hashlib
import struct
import ast
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
components=root/'custom_components'
assert [p.name for p in components.iterdir() if p.is_dir() and p.name!='__pycache__'] == ['power_out']
p=components/'power_out'
m=json.loads((p/'manifest.json').read_text())
for key in ('domain','name','version','documentation','issue_tracker','codeowners','config_flow','iot_class'):
    assert key in m,key
assert m['domain']=='power_out' and m['config_flow'] is True
assert m['requirements']==[]
for f in ('__init__.py','config_flow.py','sensor.py','binary_sensor.py','strings.json','translations/en.json','schedules.json','services.yaml','brand/icon.png','brand/icon@2x.png'):
    assert (p/f).is_file(), f
for f in p.glob('*.py'): ast.parse(f.read_text())
strings=json.loads((p/'strings.json').read_text())
assert strings==json.loads((p/'translations/en.json').read_text())
data=json.loads((p/'schedules.json').read_text())
assert hashlib.sha256((p/'schedules.json').read_bytes()).hexdigest() == '98af258d1552651382f68502e57f41304d07f254567ddefe3929a04bc25d4e35'
assert len(data)==18
assert all(len(level)==18 and all(len(row)==56 and all(type(v) is bool for v in row) for row in level) for level in data)
assert all(all(row) for row in data[17])
assert json.loads((root/'hacs.json').read_text())['name']=='UK Power Out — Reference Sensors'
assert m['documentation']=='https://github.com/sarn-online/uk-power-out#readme'
assert m['issue_tracker']=='https://github.com/sarn-online/uk-power-out/issues'
assert m['codeowners']==['@sarn-online']
for filename,size in [('icon.png',256),('icon@2x.png',512)]:
    blob=(p/'brand'/filename).read_bytes()
    assert blob[:8]==b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II',blob[16:24])==(size,size)
print('PASS: offline HACS layout, manifest structure, translations, Python syntax and 18,144 cells')
