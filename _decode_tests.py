import os, sys, base64, json

proj = os.path.dirname(os.path.abspath(__file__))
unit_dir = os.path.join(proj, 'tests', 'unit')
data_file = os.path.join(proj, '_test_data.json')

with open(data_file, 'r') as f:
    data = json.load(f)

for name, b64content in data.items():
    content = base64.b64decode(b64content).decode('utf-8')
    path = os.path.join(unit_dir, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  Written {name} ({len(content)} bytes)')

print('Done!')