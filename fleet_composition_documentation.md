# Fleet Composition Requirement Object Structure

This document outlines the structure of the `fleet_composition` object used in `data/quests/quests.json` to define fleet requirements for quests. 
The actual quest describe and requirement can be found in `reference/quests.json`.

Ship ID can be found in `tool/ship_name_api.json`
stype and ctype can be found in `tool/apilist_stype_ctype.txt`.

## Main Object: `fleet_composition`

The `fleet_composition` object contains a single key, `requirements`, which is an array of requirement objects.

-   `requirements`: An array of objects, where each object defines a specific condition that the fleet must meet.
-   `requirements_X`: `X` could be any interger, same as `requirements`, an array of objects, where each object defines a specific condition that the fleet must meet. Only defined when there is more then one way to fullfill the quest requirment, OR condition works between each `requirments`.

## Requirement Object Structure

Each object within the `requirements` array can have the following keys:

-   `id` / `stype` / `ctype` / `allowed_ship_types`: (Required) The identifier for the ship, ship type, or ship class.
    -   `id`: An array of integers for OR conditions.
    -   `stype`: An array of integers for OR conditions.
    -   `ctype`: An array of integers for OR conditions.
    -   `allowed_ship_types`: An array of ship type IDs that are allowed in the fleet. Any other ship type will invalidate the condition.

-   `count_rule`: (Optional) Defines how the `amount` is evaluated. Defaults to `at_least`.
    -   `at_least`: The fleet must have at least the specified `amount` of the required ships.
    -   `at_most`: The fleet must have at most the specified `amount` of the required ships.
    -   `exact`: The fleet must have exactly the specified `amount` of the required ships.

-   `amount`: (Optional) The number of ships required for the condition. Defaults to `1` if not specified.

-   `position`: (Optional) The 0-indexed position of the ship in the fleet. If specified, the ship must be in that exact position.


## Examples

### Example 1: At least 3 Destroyers or Coastal Defense Ships

```json
{
  "stype": [1, 2],
  "count_rule": "at_least",
  "amount": 3
}
```

### Example 2: A Light Cruiser as the flagship

```json
{
  "stype": 3,
  "position": 0
}
```

### Example 3: Exactly 3 ships of the Yamato, Nagato, Ise, or Fusou classes

```json
{
  "ctype": [37, 19, 2, 26],
  "count_rule": "exact",
  "amount": 3
}
```

### Example 4: Fleet must only contain Destroyers and Light Cruisers

```json
{
  "allowed_ship_types": [2, 3]
}
