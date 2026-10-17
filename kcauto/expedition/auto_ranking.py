import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TypedDict

from kca_enums.resources import ResourceEnum
from kca_enums.ship_types import ShipTypeEnum


class _ExpeditionData(TypedDict):
    id: int
    time: int
    reqComposition: str
    fuel: int
    ammo: int
    steel: int
    baux: int
    item: str
    itemCount: int
    fuelConsum: float
    ammoConsum: float


class _RankingRow(TypedDict):
    id: int
    score: float
    completion_utility: float


@dataclass(frozen=True)
class _ResourceState:
    active: tuple[ResourceEnum, ...]
    headroom: dict[ResourceEnum, float]
    lag: dict[ResourceEnum, float]
    overall_fill: float

    @property
    def all_zero(self) -> bool:
        return all(self.headroom[resource] == 1.0 for resource in self.active)

    @property
    def partial_zero(self) -> bool:
        return self.overall_fill == 0.0 and not self.all_zero


# Reference maximum Fuel/Ammo supply used to estimate expedition running cost.
REFERENCE_SUPPLY = {
    ShipTypeEnum.DD: (15, 15),
    ShipTypeEnum.CL: (25, 25),
    ShipTypeEnum.CVL: (35, 35),
    ShipTypeEnum.AV: (30, 15),
    ShipTypeEnum.BBV: (95, 105),
    ShipTypeEnum.SS: (10, 5),
    ShipTypeEnum.CA: (35, 55),
    ShipTypeEnum.CT: (35, 20),
    ShipTypeEnum.AS: (35, 10),
}


def _geometric_mean(values: Iterable[float]) -> float:
    values = tuple(float(value) for value in values)
    if not values:
        raise ValueError("Geometric mean requires at least one value")
    if any(value < 0 for value in values):
        raise ValueError("Geometric mean inputs must be non-negative")
    if any(value == 0 for value in values):
        return 0.0
    return math.exp(sum(math.log(value) for value in values) / len(values))


def _get_item_expected_count(
    exp_data: _ExpeditionData,
    resource: ResourceEnum,
) -> float:
    if exp_data["item"] != resource.value:
        return 0.0

    # Normal random item rewards use their expected value. Great-Success-only
    # item rewards are intentionally excluded from the static efficiency model.
    return exp_data["itemCount"] * 0.5


def _get_effective_duration(exp_data: _ExpeditionData, pooling_interval: int) -> int:
    duration = exp_data["time"]
    if duration <= 0:
        raise ValueError(f"Invalid expedition duration: {duration}")
    if pooling_interval <= 0:
        raise ValueError(f"Invalid expedition pooling interval: {pooling_interval}")
    return math.ceil(duration / pooling_interval) * pooling_interval


def _get_gross_rates(
    exp_data: _ExpeditionData,
    pooling_interval: int = 1,
) -> dict[ResourceEnum, float]:
    duration = _get_effective_duration(exp_data, pooling_interval)

    return {
        ResourceEnum.FUEL: exp_data["fuel"] / duration,
        ResourceEnum.AMMO: exp_data["ammo"] / duration,
        ResourceEnum.STEEL: exp_data["steel"] / duration,
        ResourceEnum.BAUXITE: exp_data["baux"] / duration,
        ResourceEnum.BUCKET: _get_item_expected_count(exp_data, ResourceEnum.BUCKET)
        / duration,
        ResourceEnum.DEVMAT: _get_item_expected_count(exp_data, ResourceEnum.DEVMAT)
        / duration,
    }


def _get_reference_consumption_rates(
    exp_data: _ExpeditionData,
    pooling_interval: int = 1,
) -> tuple[float, float]:
    duration = _get_effective_duration(exp_data, pooling_interval)

    fuel_ratio = exp_data["fuelConsum"] / 10
    ammo_ratio = exp_data["ammoConsum"] / 10
    fuel = 0
    ammo = 0

    for requirement in exp_data["reqComposition"].split(","):
        requirement = requirement.strip()
        match = re.fullmatch(r"(\d+)([A-Z]+)", requirement)
        if match is None:
            raise ValueError(
                f"Unsupported expedition composition requirement: {requirement}"
            )

        count = int(match.group(1))
        ship_type_name = match.group(2)
        try:
            ship_type = ShipTypeEnum[ship_type_name]
        except KeyError as exc:
            raise ValueError(
                f"Missing expedition reference supply for {ship_type_name} "
                f"in expedition {exp_data['id']}"
            ) from exc

        # Use DD as the low-consumption reference for unrestricted slots.
        if ship_type is ShipTypeEnum.NA:
            ship_type = ShipTypeEnum.DD

        if ship_type not in REFERENCE_SUPPLY:
            raise ValueError(
                f"Missing expedition reference supply for {ship_type.name} "
                f"in expedition {exp_data['id']}"
            )

        fuel_max, ammo_max = REFERENCE_SUPPLY[ship_type]
        # Preserve per-ship integer rounding before multiplying by ship count.
        fuel += count * int(fuel_max * fuel_ratio)
        ammo += count * int(ammo_max * ammo_ratio)

    return fuel / duration, ammo / duration


def _get_efficiencies(
    expeditions: Iterable[_ExpeditionData],
    pooling_interval: int = 1,
) -> dict[int, dict[ResourceEnum, float]]:
    net_rates = {}
    for exp_data in expeditions:
        exp_id = exp_data["id"]
        rates = _get_gross_rates(exp_data, pooling_interval)
        fuel_cost_rate, ammo_cost_rate = _get_reference_consumption_rates(
            exp_data, pooling_interval
        )
        rates[ResourceEnum.FUEL] -= fuel_cost_rate
        rates[ResourceEnum.AMMO] -= ammo_cost_rate
        net_rates[exp_id] = rates

    best_net_rates = {
        resource: max((rates[resource] for rates in net_rates.values()), default=0.0)
        for resource in ResourceEnum
    }

    # E[e,r] = netRate[e,r] / bestNetRate[r]
    #
    # Normalize each resource against the same net-production quantity used in
    # the numerator, so the best attainable net producer defines E = 1.
    return {
        exp_id: {
            resource: (
                rates[resource] / best_net_rates[resource]
                if best_net_rates[resource] > 0
                else 0.0
            )
            for resource in ResourceEnum
        }
        for exp_id, rates in net_rates.items()
    }


def _get_resource_state(
    current: Mapping[ResourceEnum, float],
    desire: Mapping[ResourceEnum, float],
) -> _ResourceState:
    active = tuple(resource for resource in ResourceEnum if desire[resource] > 0)
    if not active:
        raise ValueError("At least one expedition resource desire must be positive")

    # x_r = min(1, current_r / desire_r)
    # H_r = 1 - x_r
    fill = {
        resource: min(1.0, max(0.0, current[resource] / desire[resource]))
        for resource in active
    }
    headroom = {resource: 1.0 - fill[resource] for resource in active}
    # d(r,s) = 0 if x_r >= x_s else 1 - x_r / x_s
    # L_r = mean_s(d(r,s)), s != r
    #
    # Compare each resource directly with every active peer instead of first
    # collapsing the peer set into one reference value. Only a richer peer
    # contributes lag, which naturally handles equal and zero-valued peers
    # without a separate zero branch or an arbitrary epsilon.
    lag = {}
    for resource in active:
        peers = [value for peer, value in fill.items() if peer is not resource]
        if not peers:
            lag[resource] = 0.0
            continue

        lag[resource] = sum(
            0.0 if fill[resource] >= peer_fill else 1.0 - fill[resource] / peer_fill
            for peer_fill in peers
        ) / len(peers)

    return _ResourceState(
        active=active,
        headroom=headroom,
        lag=lag,
        # F = GM(x_r). F weights target completion against relative balance.
        overall_fill=_geometric_mean(fill.values()),
    )


def rank_expeditions(
    expeditions: Iterable[_ExpeditionData],
    current: Mapping[ResourceEnum, float],
    desire: Mapping[ResourceEnum, float],
    pooling_interval: int = 1,
) -> list[_RankingRow]:
    """Rank a pre-filtered auto-expedition candidate pool.

    Resource state
    --------------
    For each active resource r:

        x_r = min(1, max(0, current_r / desire_r))
        H_r = 1 - x_r
        d(r,s) = 0 if x_r >= x_s else 1 - x_r / x_s
        L_r = mean_s(d(r,s)), s != r
        F = GM(x_r)

    H_r measures remaining target headroom, L_r measures mean pairwise
    relative lag, and F is overall fill. Low F emphasizes relative balance;
    high F emphasizes finishing the remaining configured targets.

    Expedition efficiency
    ---------------------
    For expedition e and resource r:

        effectiveDuration[e] = ceil(actualDuration[e] / poolingInterval) * poolingInterval
        E[e,r] = netRate[e,r] / bestNetRate[r]

    Both rewards and one-time reference fleet Fuel/Ammo costs use the same
    effective duration (in minutes). Normal random item rewards use expected
    value. bestNetRate is taken over the pre-filtered candidate pool.

    Utilities and score
    ----------------------------
    For expedition e:

        U_e = sum_r(H_r * E[e,r])
        B_e = sum_r(L_r * E[e,r])
        Score_e = F * U_e + (1 - F) * B_e

    U_e measures target-completion utility and B_e measures relative-balance
    utility.

    Zero boundaries
    ---------------
    Geometric mean becomes zero when any active resource is zero. At
    partial-zero, F = 0 makes the general formula reduce naturally to B, with
    U used only as an exact-score tie-break. At all-zero, every pairwise lag
    is also zero, so B = 0 and ranking falls back to U.
    """
    expeditions = tuple(expeditions)
    if not expeditions:
        return []

    efficiencies = _get_efficiencies(expeditions, pooling_interval)
    state = _get_resource_state(current, desire)
    rows = []

    for exp_data in expeditions:
        exp_id = exp_data["id"]
        efficiency = efficiencies[exp_id]
        completion_utility = sum(
            state.headroom[resource] * efficiency[resource] for resource in state.active
        )
        balance_utility = sum(
            state.lag[resource] * efficiency[resource] for resource in state.active
        )

        if state.all_zero:
            score = completion_utility
        else:
            fill = state.overall_fill
            score = fill * completion_utility + (1 - fill) * balance_utility

        rows.append(
            {
                "id": exp_id,
                "score": score,
                "completion_utility": completion_utility,
            }
        )

    if state.partial_zero:
        rows.sort(
            key=lambda row: (
                -row["score"],
                -row["completion_utility"],
                row["id"],
            )
        )
    else:
        rows.sort(key=lambda row: (-row["score"], row["id"]))

    return rows
