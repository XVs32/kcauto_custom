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

## Required POI plugins

kcauto checks for these plugins before it connects and prints the install
commands when one is missing or too old. Restart POI after installing.

| Plugin | Purpose |
| --- | --- |
| `poi-plugin-forwarder` (>= 1.1.0) | Forwards KCSAPI and map resources, hosts the interaction service on the control port |
| `poi-plugin-noro6-exporter` | Exports ships and equipment to Noro6 |

Plugins live in `<POI data dir>/plugins`, usually:

* Windows: `%APPDATA%\poi\plugins`
* Linux: `~/.config/poi/plugins`
* macOS: `~/Library/Preferences/poi/plugins`

Install them from POI's plugin settings tab, or from a shell:

```sh
cd "<POI data dir>/plugins"
npm install "git+https://github.com/pmsleepcheck/poi-plugin-api-forwarder.git#feature/poi-interaction-server" --allow-git=all
npm install poi-plugin-noro6-exporter
```

The interaction service ships with `poi-plugin-forwarder` 1.1.0 and newer.
Older releases only forward KCSAPI, so the control port stays closed.

## Ports

| Setting | Default | Served by |
| --- | --- | --- |
| `general.poi_api_port` | 9223 | kcauto, receives the webhook POSTs |
| `general.poi_control_port` | 38591 | the POI plugin, kcauto connects to it |
