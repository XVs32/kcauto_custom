_Out of clutter, find simplicity._

---

## Config setting flow

kcauto_custom is basically a standalone program runs with a config file. 

The CUI(Command line User Interface) we use is just a config file editor,  
it makes kcauto_custom easier to use, but it is not a must. 

You can for sure edit the config file with notepad and runs kcauto_custom with it.

![image](https://github.com/XVs32/kcauto_custom/assets/16824564/6bd97995-62ba-4692-9c68-7b81315ecfbc)

---

## KCAuto Configuration File Documentation

## Overview

KCAuto uses JSON configuration files to control its behavior. The configuration system is modular,  
with different sections controlling different aspects of the automation. 

All configuration files must be valid JSON format.

## File Format

Configuration files are JSON objects with dot-notation keys.  
Each key follows the pattern `<module>.<setting>`.

### Example Basic Structure
```json
{
    "general.interaction_mode": "chrome_driver",
    "general.jst_offset": 0,
    "combat.enabled": true,
    "combat.sortie_map": "1-1",
    "expedition.enabled": false
}
```

## Configuration Modules

### General Settings (`general.*`)

Controls basic application behavior and browser interaction.

#### `general.interaction_mode`
- **Type**: string
- **Valid Values**: `"chrome_driver"`, `"direct_control"`, `"poi"`
- **Default**: `"chrome_driver"`
- **Description**: Determines how kcauto interacts with the browser.  
Chrome driver mode sends control signals through Chrome DevTools, direct
control mode uses the desktop mouse, and POI mode uses the API Forwarder
plugin's loopback screenshot and input service.

#### `general.jst_offset`
- **Type**: integer
- **Valid Range**: -20 to 20
- **Default**: 0
- **Description**: Time offset in hours from JST (Japan Standard Time) for scheduling and time-based operations.

#### `general.chrome_dev_port`
- **Type**: integer
- **Valid Range**: 0 to 65535
- **Default**: 9222
- **Description**: Port number for Chrome DevTools Protocol connection.  
Do not change if you don't know what you're doing.

#### `general.poi_api_port`
- **Type**: integer
- **Valid Range**: 0 to 65535
- **Default**: 9223
- **Description**: Port number for POI API forwarding.  
Do not change if you don't know what you're doing.

#### `general.poi_control_port`
- **Type**: integer
- **Valid Range**: 0 to 65535
- **Default**: 38591
- **Description**: Loopback port for POI screenshots and input when
`general.interaction_mode` is `"poi"`.

#### ~~`general.paused`~~ Not working at the moment(2025/07/17)
- **Type**: boolean
- **Default**: false
- **Description**: Whether kcauto should start in paused state.

### Combat Settings (`combat.*`)

Controls sortie and combat behavior.

#### `combat.enabled`
- **Type**: boolean
- **Default**: false
- **Description**: Enables or disables the combat module entirely.

#### `combat.sortie_map`
- **Type**: string
- **Valid Format**: Map notation like "1-1", "3-5", "6-4", or "auto"
- **Default**: "1-1"
- **Description**: Specifies which map to sortie to. Use "auto" for automatic map selection.
- **Example**: `"1-1"`, `"3-5"`, `"E-1"`, `"auto"`

#### `combat.fleet_mode`
- **Type**: string
- **Valid Values**: `"standard"`, `"strike"`, `"tcf"`, `"ctf"`, `"stf"`
- **Default**: `"standard"`
- **Description**: Defines the fleet formation mode for combat.
  - `"standard"`: Single fleet
  - `"strike"`: Strike force (uses fleet 3)
  - `"tcf"`: Transport Combined Fleet
  - `"ctf"`: Carrier Task Force
  - `"stf"`: Surface Task Force

#### `combat.fleet_presets`
- **Type**: array of integers or strings
- **Valid Values**: Numbers 1-15 or `"auto"`
- **Default**: `[]`
- **Description**: List of fleet preset numbers to use for combat. Use `"auto"` for automatic fleet selection.
- **Example**: `[1, 2, 3]`, `["auto"]`

#### `combat.check_fatigue`
- **Type**: boolean
- **Default**: true
- **Description**: Whether kcauto should check ship fatigue levels during combat operations.

#### `combat.check_lbas_fatigue`
- **Type**: boolean
- **Default**: true
- **Description**: Whether kcauto should check Land-Based Air Squadron (LBAS) fatigue during combat.

#### `combat.clear_stop`
- **Type**: boolean
- **Default**: false
- **Description**: Whether kcauto should stop combat operations when the map has been cleared.

#### `combat.port_check`
- **Type**: boolean
- **Default**: false
- **Description**: Whether to check port capacity before sorties.

#### `combat.reserve_repair_dock`
- **Type**: boolean
- **Default**: true
- **Description**: Whether to reserve repair dock slots for emergency repairs.

#### `combat.retreat_limit`
- **Type**: integer
- **Valid Values**: 0-4 (damage state levels)
- **Default**: 4
- **Description**: Damage threshold for retreating ships. Values correspond to damage states:
  - 0: No damage
  - 1: Scratch damage
  - 2: Minor damage
  - 3: Moderate damage
  - 4: Heavy damage

#### `combat.repair_limit`
- **Type**: integer
- **Valid Values**: 0-4 (damage state levels)
- **Default**: 3
- **Description**: Damage threshold for automatically repairing ships.

#### `combat.repair_bucket_threshold`
- **Type**: integer
- **Default**: 500
- **Description**: Minimum number of repair buckets to maintain before using them for repairs.

#### `combat.repair_timelimit_hours`
- **Type**: integer
- **Default**: 0
- **Description**: Maximum hours to wait for natural repair before using buckets.

#### `combat.repair_timelimit_minutes`
- **Type**: integer
- **Valid Range**: 0-59
- **Default**: 0
- **Description**: Maximum minutes to wait for natural repair before using buckets.

#### `combat.retreat_points`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: List of node names where the fleet should retreat.
- **Example**: `["A", "B", "C"]`

#### `combat.push_nodes` (**!!DANGER!! 大破進擊警告!!**)
- **Type**: array of strings
- **Default**: `[]`
- **Description**: List of node names where the fleet should push forward regardless of damage.
- **Example**: `["D", "Z"]`

#### `combat.node_selects`
- **Type**: array of strings
- **Format**: `"source_node>target_node"`
- **Default**: `[]`
- **Description**: Specifies node routing choices at branching points.
- **Example**: `["A>B", "C>D"]`

#### `combat.node_formations`
- **Type**: array of strings
- **Format**: `"node:formation"`
- **Valid formations**: `line_ahead`, `double_line`, `diamond`, `echelon`, `line_abreast`, `vanguard`, `combined_fleet_1`, `combined_fleet_2`, `combined_fleet_3`, `combined_fleet_4`
- **Default**: `[]`
- **Description**: Specifies formation to use at specific nodes.
- **Example**: `["A:line_ahead", "B:double_line"]`

#### `combat.node_night_battles`
- **Type**: array of strings
- **Format**: `"node:True/False"`
- **Default**: `[]`
- **Description**: Specifies whether to engage in night battle at specific nodes.
- **Example**: `["X:True", "A:False"]`

#### `combat.node_smoke`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: List of nodes where smoke screen should be used.
- **Example**: `["A", "B"]`

#### `combat.lbas_groups`
- **Type**: array of strings
- **Valid Values**: `"1"`, `"2"`, `"3"`
- **Default**: `[]`
- **Description**: List of LBAS groups to activate.
- **Example**: `["1", "2"]`

#### `combat.lbas_group_1_nodes`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: Target nodes for LBAS Group 1. Must specify exactly 0 or 2 nodes.
- **Example**: `["A", "A"]`

#### `combat.lbas_group_2_nodes`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: Target nodes for LBAS Group 2. Must specify exactly 0 or 2 nodes.

#### `combat.lbas_group_3_nodes`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: Target nodes for LBAS Group 3. Must specify exactly 0 or 2 nodes.

#### `combat.override`
- **Type**: boolean
- **Default**: false
- **Description**: Whether to allow configuration overrides during runtime.

### Expedition Settings (`expedition.*`)

Controls expedition management and resource gathering.

#### `expedition.enabled`
- **Type**: boolean
- **Default**: true
- **Description**: Enables or disables the expedition module.

#### `expedition.fleet_2`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: List of expedition IDs to assign to fleet 2. Use `"auto"` for automatic selection.
- **Example**: `[2, 4, 5]`, `["auto"]`

#### `expedition.fleet_3`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: List of expedition IDs to assign to fleet 3.

#### `expedition.fleet_4`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: List of expedition IDs to assign to fleet 4.

#### `expedition.fleet_preset`
- **Type**: string or null
- **Valid Values**: `"auto"` or null
- **Default**: null
- **Description**: Fleet preset mode for expeditions. Currently only supports "auto" or null.

#### `expedition.desire_oil`
- **Type**: integer
- **Valid Range**: 0-350000
- **Default**: 350000
- **Description**: Target amount of fuel to maintain through expeditions.

#### `expedition.desire_ammo`
- **Type**: integer
- **Valid Range**: 0-350000
- **Default**: 350000
- **Description**: Target amount of ammunition to maintain.

#### `expedition.desire_steel`
- **Type**: integer
- **Valid Range**: 0-350000
- **Default**: 350000
- **Description**: Target amount of steel to maintain.

#### `expedition.desire_bauxite`
- **Type**: integer
- **Valid Range**: 0-350000
- **Default**: 350000
- **Description**: Target amount of bauxite to maintain.

#### `expedition.desire_bucket`
- **Type**: integer
- **Valid Range**: 0-3000
- **Default**: 3000
- **Description**: Target number of repair buckets to maintain.

### PvP Settings (`pvp.*`)

Controls Player vs Player combat behavior.

#### `pvp.enabled`
- **Type**: boolean
- **Default**: false
- **Description**: Enables or disables PvP combat. Cannot be enabled when combat fleet is in combined mode.

#### `pvp.fleet_preset`
- **Type**: integer, string, or null
- **Valid Values**: 1-15, `"auto"`, or null
- **Default**: 0
- **Description**: Fleet preset to use for PvP battles. Use `"auto"` for automatic selection.

### Quest Settings (`quest.*`)

Controls daily/weekly/monthly quest management.

#### `quest.enabled`
- **Type**: boolean
- **Default**: true
- **Description**: Enables or disables automatic quest management.

#### `quest.quests`
- **Type**: array of strings
- **Default**: `[]`
- **Description**: List of quest IDs to automatically accept and complete.
- **Example**: `["Bd1", "Bd2", "Bw1", "C2", "D2"]`

### Factory Settings (`factory.*`)

Controls ship construction and equipment development.

#### `factory.enabled`
- **Type**: boolean
- **Default**: false
- **Description**: Enables or disables factory operations.

#### `factory.build_recipe`
- **Type**: array of 4 integers
- **Default**: `[30, 30, 30, 30]`
- **Description**: Resource recipe for ship construction [fuel, ammo, steel, bauxite].

#### `factory.build_secretary`
- **Type**: integer
- **Default**: 1234
- **Description**: Ship ID to use as secretary for ship construction.

#### `factory.develop_recipe`
- **Type**: array of 4 integers
- **Default**: `[10, 10, 10, 10]`
- **Description**: Resource recipe for equipment development [fuel, ammo, steel, bauxite].

#### `factory.develop_secretary`
- **Type**: integer
- **Default**: 1234
- **Description**: Ship ID to use as secretary for equipment development.

### Scheduler Settings (`scheduler.*`)

Controls time-based automation rules.

#### `scheduler.enabled`
- **Type**: boolean
- **Default**: true
- **Description**: Enables or disables the scheduler system.

#### `scheduler.rules`
- **Type**: array of strings
- **Format**: `"condition:value:action:module"` or `"condition:value:action:module:extra"`
- **Default**: `[]`
- **Description**: List of scheduler rules that trigger actions based on conditions.
- **Example**: 
  ```json
  [
    "time:0230:stop:kcauto",
    "sorties_run:15:stop:combat"
  ]
  ```

### Passive Repair Settings (`passive_repair.*`)

Controls automatic repair dock management.

#### `passive_repair.enabled`
- **Type**: boolean
- **Default**: false
- **Description**: Enables or disables passive repair management.

#### `passive_repair.repair_threshold`
- **Type**: integer
- **Valid Values**: 1-4 (damage state levels)
- **Default**: 1
- **Description**: Minimum damage level required to trigger passive repair.

#### `passive_repair.slots_to_reserve`
- **Type**: integer
- **Default**: 2
- **Description**: Number of repair dock slots to keep available for emergency repairs.

### Ship Switcher Settings (`ship_switcher.*`)

Controls automatic ship switching and management.

#### `ship_switcher.enabled`
- **Type**: boolean
- **Default**: false
- **Description**: Enables or disables automatic ship switching.

#### `ship_switcher.slots`
- **Type**: object
- **Default**: `{}`
- **Description**: Configuration for ship switching rules per fleet slot.

### Event Reset Settings (`event_reset.*`)

Controls event map reset behavior for farming.

#### `event_reset.enabled`
- **Type**: boolean
- **Default**: false
- **Description**: Enables or disables event reset functionality.

#### `event_reset.farm_difficulty`
- **Type**: integer
- **Valid Values**: 1-4 (difficulty levels)
- **Default**: 2
- **Description**: Difficulty level to use for farming runs.

#### `event_reset.reset_difficulty`
- **Type**: integer
- **Valid Values**: 1-4 (difficulty levels)
- **Default**: 3
- **Description**: Difficulty level to reset to after farming.

#### `event_reset.frequency`
- **Type**: integer
- **Default**: 3
- **Description**: Number of farming runs before triggering a reset.

---

## Best Practices

1. **Start Simple**: Begin with basic configurations and gradually add complexity
2. **Test Incrementally**: Enable one module at a time to verify behavior
3. **Use Templates**: Base your configuration on provided templates
4. **Validate Settings**: Ensure all values are within valid ranges and formats
5. **Monitor Logs**: Check logs for configuration warnings and errors
6. **Backup Configs**: Keep backups of working configurations

---

## Configuration Examples

### Basic Combat Configuration
```json
{
    "general.interaction_mode": "chrome_driver",
    "general.jst_offset": 0,
    "combat.enabled": true,
    "combat.sortie_map": "1-1",
    "combat.fleet_mode": "standard",
    "combat.fleet_presets": [1],
    "combat.check_fatigue": true,
    "combat.retreat_limit": 3,
    "expedition.enabled": false,
    "pvp.enabled": false,
    "quest.enabled": false
}
```

### Expedition Farming Configuration
```json
{
    "general.interaction_mode": "chrome_driver",
    "combat.enabled": false,
    "expedition.enabled": true,
    "expedition.fleet_2": ["2", "3"],
    "expedition.fleet_3": ["5", "6"],
    "expedition.fleet_4": ["37", "38"],
    "expedition.desire_oil": 300000,
    "expedition.desire_ammo": 300000,
    "expedition.desire_steel": 300000,
    "expedition.desire_bauxite": 300000,
    "quest.enabled": true,
    "quest.quests": ["Bd1", "Bd2", "Bd3"]
}
```

### Combined Fleet Combat Configuration
```json
{
    "combat.enabled": true,
    "combat.fleet_mode": "ctf",
    "combat.sortie_map": "6-4",
    "combat.fleet_presets": [1],
    "combat.lbas_groups": ["1", "2"],
    "combat.lbas_group_1_nodes": ["A", "A"],
    "combat.lbas_group_2_nodes": ["B", "Z"],
    "combat.node_formations": ["A:line_ahead", "Z:line_ahead"],
    "combat.node_night_battles": ["A:True"],
    "expedition.enabled": false,
    "pvp.enabled": false
}
```

### Auto Mode Configuration
```json
{
    "combat.enabled": true,
    "combat.sortie_map": "auto",
    "combat.fleet_presets": ["auto"],
    "expedition.enabled": true,
    "expedition.fleet_preset": "auto",
    "expedition.fleet_2": ["auto"],
    "expedition.fleet_3": ["auto"],
    "expedition.fleet_4": ["auto"],
    "pvp.enabled": true,
    "pvp.fleet_preset": "auto"
}
```


