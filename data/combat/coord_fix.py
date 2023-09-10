import json

# Open the file for reading
with open('E-1.json', 'r') as f:
    data = json.load(f)

# Modify the data
for node in data['nodes'].values():
    node['coords'][0] += 20
    node['coords'][1] += 27

# Open the file for writing
with open('E-1.json', 'w') as f:
    json.dump(data, f, indent=4)