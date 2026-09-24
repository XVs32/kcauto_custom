from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

from ships.equipment import Equipment

if TYPE_CHECKING:
    from fleet.fleet import Fleet
    from ships.ship import Ship


class EquipmentStarPreference(Enum):
    CLOSEST = "closest"
    HIGHEST = "highest"
    ANY = "any"


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
    def display_name(self) -> str:
        if self.is_reinforcement:
            return "slot_ex"
        return f"slot {self.value + 1}"


@dataclass(frozen=True, slots=True)
class EquipmentSlotRef:
    ship_id: int
    slot: EquipmentSlot


@dataclass(frozen=True, slots=True)
class EquipmentRequirement:
    ship: Ship
    slot: EquipmentSlot
    model_id: int
    equipment_name: str
    star_preference: EquipmentStarPreference
    stars: int

    @classmethod
    def from_target_equipment(
        cls,
        ship: Ship,
        slot: EquipmentSlot,
        equipment: Equipment,
        star_preference: EquipmentStarPreference = EquipmentStarPreference.CLOSEST,
    ) -> EquipmentRequirement:
        return cls(
            ship=ship,
            slot=slot,
            model_id=equipment.model_id,
            equipment_name=equipment.name,
            star_preference=star_preference,
            stars=equipment.stars,
        )

    def star_priority(self, equipment: Equipment) -> int:
        if self.star_preference is EquipmentStarPreference.HIGHEST:
            return -equipment.stars
        if self.star_preference is EquipmentStarPreference.ANY:
            return 0
        return abs(equipment.stars - self.stars)

    @property
    def requested_star_description(self) -> str:
        if self.star_preference is EquipmentStarPreference.HIGHEST:
            return "highest available star level"
        if self.star_preference is EquipmentStarPreference.ANY:
            return "any star level"
        return f"{self.stars}★"


@dataclass(frozen=True, slots=True)
class MovableEquipment:
    equipment: Equipment
    source_ship: Optional[Ship]
    source_slot: Optional[EquipmentSlot]

    @property
    def is_free(self) -> bool:
        return self.source_ship is None


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

    def assign(self, ship: Ship, slot: EquipmentSlot, equipment: Equipment) -> None:
        ref = EquipmentSlotRef(ship.production_id, slot)
        if ref in self._assignments:
            raise ValueError(f"Equipment slot {ref} is already assigned")
        if equipment.production_id in self._assigned_equipment_ids:
            raise ValueError(f"Equipment {equipment.production_id} is already assigned")
        if equipment.production_id == Equipment.UNKNOWN_PRODUCTION_ID:
            raise ValueError("Equipment plan requires a physical production ID")

        self._assignments[ref] = equipment
        self._assigned_equipment_ids.add(equipment.production_id)

    def unassign(self, ship: Ship, slot: EquipmentSlot) -> None:
        ref = EquipmentSlotRef(ship.production_id, slot)
        equipment = self._assignments.pop(ref)
        self._assigned_equipment_ids.remove(equipment.production_id)

    def equipment_for(self, ship: Ship, slot: EquipmentSlot) -> Equipment:
        return self._assignments[EquipmentSlotRef(ship.production_id, slot)]

    def is_equipment_assigned(self, production_id: int) -> bool:
        return production_id in self._assigned_equipment_ids

    def equipment_for_ship_ids(self, ship_ids: list[int]) -> list[Equipment]:
        return [
            equipment
            for slot_ref, equipment in self._assignments.items()
            if slot_ref.ship_id in ship_ids
        ]


class EquipmentAllocator:
    def __init__(self, plan: EquipmentPlan):
        self.plan = plan

    def _get_allocation_priority(
        self,
        requirement: EquipmentRequirement,
        movable_equipment: MovableEquipment,
    ) -> tuple[int, int, int, int]:
        equipment = movable_equipment.equipment
        same_slot_priority = int(
            movable_equipment.source_ship is None
            or movable_equipment.source_ship.production_id
            != requirement.ship.production_id
            or movable_equipment.source_slot is not requirement.slot
        )
        source_priority = 0 if movable_equipment.is_free else 1

        return (
            requirement.star_priority(equipment),
            same_slot_priority,
            source_priority,
            equipment.production_id,
        )

    def _get_candidates(
        self,
        requirement: EquipmentRequirement,
        movable_equipment_by_id: dict[int, MovableEquipment],
    ) -> list[MovableEquipment]:
        import ships.equipment_core as equ

        candidates = [
            movable_equipment
            for movable_equipment in movable_equipment_by_id.values()
            if movable_equipment.equipment.model_id == requirement.model_id
            and not self.plan.is_equipment_assigned(
                movable_equipment.equipment.production_id
            )
            and (
                requirement.slot is not EquipmentSlot.REINFORCEMENT
                or equ.equipment.is_reinforcement_equipment_available(
                    requirement.ship, movable_equipment.equipment
                )
            )
        ]
        return sorted(
            candidates,
            key=lambda movable_equipment: self._get_allocation_priority(
                requirement, movable_equipment
            ),
        )

    def _assign_requirements(
        self,
        requirements: list[EquipmentRequirement],
        movable_equipment_by_id: dict[int, MovableEquipment],
    ) -> bool:
        if not requirements:
            return True

        requirement_candidates = [
            (
                requirement,
                self._get_candidates(requirement, movable_equipment_by_id),
            )
            for requirement in requirements
        ]
        requirement, candidates = min(
            requirement_candidates, key=lambda item: len(item[1])
        )
        if not candidates:
            return False

        remaining_requirements = [
            remaining
            for remaining in requirements
            if remaining is not requirement
        ]
        for movable_equipment in candidates:
            self.plan.assign(
                requirement.ship, requirement.slot, movable_equipment.equipment
            )
            if self._assign_requirements(remaining_requirements, movable_equipment_by_id):
                return True
            self.plan.unassign(requirement.ship, requirement.slot)

        return False

    def allocate(
        self,
        requirements: list[EquipmentRequirement],
        movable_equipment_by_id: dict[int, MovableEquipment],
    ) -> bool:
        from util.logger import Log

        if not self._assign_requirements(requirements, movable_equipment_by_id):
            Log.log_error(
                "Cannot find a conflict-free equipment allocation for all target slots."
            )
            return False

        for requirement in requirements:
            selected_equipment = self.plan.equipment_for(
                requirement.ship, requirement.slot
            )

            if (
                requirement.star_preference is not EquipmentStarPreference.CLOSEST
                or selected_equipment.stars == requirement.stars
            ):
                continue

            Log.log_warn(
                f"Using {selected_equipment.name} {selected_equipment.stars}★ "
                f"({selected_equipment.production_id}) instead of requested "
                f"{requirement.equipment_name} {requirement.stars}★ "
                f"(model {requirement.model_id}) for "
                f"{requirement.ship.name_jp} {requirement.slot.display_name}."
            )

        return True
