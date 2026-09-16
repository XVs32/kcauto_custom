from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from ships.equipment import Equipment

if TYPE_CHECKING:
    from fleet.fleet import Fleet
    from ships.ship import Ship


class EquipmentSlot(Enum):
    SLOT_1 = 0
    SLOT_2 = 1
    SLOT_3 = 2
    SLOT_4 = 3
    SLOT_5 = 4
    REINFORCEMENT = 99

    @classmethod
    def from_index(cls, index: int) -> EquipmentSlot:
        return cls(index)

    @property
    def is_reinforcement(self) -> bool:
        return self is EquipmentSlot.REINFORCEMENT

    @property
    def normal_index(self) -> int:
        if self.is_reinforcement:
            raise ValueError("Reinforcement slot has no normal slot index")
        return self.value

    @property
    def display_name(self) -> str:
        if self.is_reinforcement:
            return "slot_ex"
        return f"slot {self.normal_index + 1}"


@dataclass(frozen=True, slots=True)
class EquipmentSlotRef:
    ship_id: int
    slot: EquipmentSlot


@dataclass(slots=True)
class EquipmentPlan:
    targets: list[tuple[int, Fleet]] = field(default_factory=list)
    _assignments: dict[EquipmentSlotRef, Equipment] = field(default_factory=dict)
    _assigned_equipment_ids: set[int] = field(default_factory=set)

    def clear(self) -> None:
        self.targets.clear()
        self.clear_assignments()

    def clear_assignments(self) -> None:
        self._assignments.clear()
        self._assigned_equipment_ids.clear()

    def set_targets(self, targets: list[tuple[int, Fleet]]) -> None:
        self.targets = list(targets)

    def assign(
        self, ship: Ship, slot: EquipmentSlot, equipment: Equipment
    ) -> None:
        ref = EquipmentSlotRef(ship.production_id, slot)
        self._assignments[ref] = equipment
        self._assigned_equipment_ids.add(equipment.production_id)

    def has_assignment(self, ship: Ship, slot: EquipmentSlot) -> bool:
        return EquipmentSlotRef(ship.production_id, slot) in self._assignments

    def equipment_for(
        self, ship: Ship, slot: EquipmentSlot
    ) -> Equipment | None:
        return self._assignments.get(EquipmentSlotRef(ship.production_id, slot))

    def is_equipment_assigned(self, production_id: int) -> bool:
        return production_id in self._assigned_equipment_ids

    def items(self):
        return self._assignments.items()
