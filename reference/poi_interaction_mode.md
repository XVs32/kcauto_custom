# POI interaction mode

Set `general.interaction_mode` to `poi` when KanColle runs inside POI. The API
Forwarder plugin must be enabled with matching ports:

```json
"general.interaction_mode": "poi",
"general.poi_api_port": 9223,
"general.poi_control_port": 38591
```

The webhook port supplies KCSAPI and map-resource events. The control port is
loopback-only and supplies logical 1200x720 game captures, mouse input,
refresh, and POI quest data. POI mode does not require Chrome's remote
debugging port and continues to capture the game while its window is covered.

`direct_control` and `chrome_driver` keep their existing behavior.
