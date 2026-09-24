from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Optional, Sequence

from ships.equipment import Equipment


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
class FleetTarget:
    fleet_id: int
    ship_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class EquipmentRequirement:
    slot_ref: EquipmentSlotRef
    model_id: int
    star_preference: EquipmentStarPreference
    stars: int

    @classmethod
    def from_target_equipment(
        cls,
        ship_id: int,
        slot: EquipmentSlot,
        equipment: Equipment,
        star_preference: EquipmentStarPreference = EquipmentStarPreference.CLOSEST,
    ) -> EquipmentRequirement:
        return cls(
            slot_ref=EquipmentSlotRef(ship_id, slot),
            model_id=equipment.model_id,
            star_preference=star_preference,
            stars=equipment.stars,
        )

    def star_priority(self, equipment: Equipment) -> int:
        if self.star_preference is EquipmentStarPreference.HIGHEST:
            return -equipment.stars
        if self.star_preference is EquipmentStarPreference.ANY:
            return 0
        return abs(equipment.stars - self.stars)


@dataclass(frozen=True, slots=True)
class MovableEquipment:
    equipment: Equipment
    source_ref: Optional[EquipmentSlotRef]

    @property
    def is_free(self) -> bool:
        return self.source_ref is None


class EquipmentAllocationFailure(Exception):
    def __init__(self, requirement: EquipmentRequirement):
        self.requirement = requirement
        super().__init__(f"Unable to allocate equipment model {requirement.model_id}.")


@dataclass(frozen=True, slots=True)
class EquipmentPlan:
    targets: tuple[FleetTarget, ...] = ()
    assignments: Mapping[EquipmentSlotRef, Equipment] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assignments",
            MappingProxyType(dict(self.assignments)),
        )

    def equipment_for(self, slot_ref: EquipmentSlotRef) -> Optional[Equipment]:
        return self.assignments.get(slot_ref)

    def equipment_for_ship_ids(self, ship_ids: Sequence[int]) -> list[Equipment]:
        target_ship_ids = set(ship_ids)
        return [
            equipment
            for slot_ref, equipment in self.assignments.items()
            if slot_ref.ship_id in target_ship_ids
        ]


class EquipmentAllocator:
    def _get_allocation_priority(
        self,
        requirement: EquipmentRequirement,
        movable_equipment: MovableEquipment,
    ) -> tuple[int, int, int, int]:
        equipment = movable_equipment.equipment
        same_slot = movable_equipment.source_ref == requirement.slot_ref
        same_slot_priority = int(not same_slot)
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
        movable_equipments: list[MovableEquipment],
        assigned_equipment_ids: set[int],
        reinforcement_eligible_ids: dict[int, set[int]],
    ) -> list[MovableEquipment]:
        candidates = [
            movable_equipment
            for movable_equipment in movable_equipments
            if movable_equipment.equipment.model_id == requirement.model_id
            and movable_equipment.equipment.production_id not in assigned_equipment_ids
            and (
                not requirement.slot_ref.slot.is_reinforcement
                or movable_equipment.equipment.production_id
                in reinforcement_eligible_ids[requirement.slot_ref.ship_id]
            )
        ]
        return sorted(
            candidates,
            key=lambda movable_equipment: self._get_allocation_priority(
                requirement, movable_equipment
            ),
        )

    def allocate(
        self,
        targets: tuple[FleetTarget, ...],
        requirements: list[EquipmentRequirement],
        movable_equipments: list[MovableEquipment],
        reinforcement_eligible_ids: dict[int, set[int]],
    ) -> EquipmentPlan:
        assignments: dict[EquipmentSlotRef, Equipment] = {}
        assigned_equipment_ids: set[int] = set()

        def search(remaining_requirements: list[EquipmentRequirement]) -> None:
            if not remaining_requirements:
                return

            requirement_candidates = [
                (
                    requirement,
                    self._get_candidates(
                        requirement,
                        movable_equipments,
                        assigned_equipment_ids,
                        reinforcement_eligible_ids,
                    ),
                )
                for requirement in remaining_requirements
            ]
            requirement, candidates = min(
                requirement_candidates, key=lambda item: len(item[1])
            )
            if not candidates:
                raise EquipmentAllocationFailure(requirement)

            next_requirements = [
                remaining
                for remaining in remaining_requirements
                if remaining is not requirement
            ]
            last_failure = EquipmentAllocationFailure(requirement)
            for movable_equipment in candidates:
                equipment = movable_equipment.equipment
                assignments[requirement.slot_ref] = equipment
                assigned_equipment_ids.add(equipment.production_id)

                try:
                    search(next_requirements)
                    return
                except EquipmentAllocationFailure as failure:
                    del assignments[requirement.slot_ref]
                    assigned_equipment_ids.remove(equipment.production_id)
                    last_failure = failure

            raise last_failure

        search(requirements)

        return EquipmentPlan(
            targets=targets,
            assignments=assignments,
        )
