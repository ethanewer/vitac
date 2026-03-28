#!/bin/bash
python3 -c "
import json
with open('/app/config/settings.json') as f:
    d = json.load(f)
d['port'] = 8080
d['debug'] = False
d['database']['host'] = 'db.prod.internal'
with open('/app/config/settings.json', 'w') as f:
    json.dump(d, f, indent=2)
"
