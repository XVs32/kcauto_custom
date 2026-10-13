import math
import re
from dataclasses import dataclass

from kca_enums.ship_types import ShipTypeEnum


RESOURCE_NAMES = ("fuel", "ammo", "steel", "bauxite", "bucket", "devmat")


@dataclass(frozen=True)
class _ResourceState:
    active: tuple[str, ...]
    headroom: dict[str, float]
    lag: dict[str, float]
    overall_fill: float

    @property
    def all_zero(self):
        return all(
            self.headroom[resource] == 1.0 for resource in self.active
        )

    @property
    def partial_zero(self):
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


def _geometric_mean(values):
    values = tuple(float(value) for value in values)
    if not values:
        raise ValueError("Geometric mean requires at least one value")
    if any(value < 0 for value in values):
        raise ValueError("Geometric mean inputs must be non-negative")
    if any(value == 0 for value in values):
        return 0.0
    return math.exp(sum(math.log(value) for value in values) / len(values))


def _get_item_expected_count(exp_data, item_name):
    if exp_data["item"] != item_name:
        return 0.0

    # Normal random item rewards use their expected value. Great-Success-only
    # item rewards are intentionally excluded from the static coefficient.
    return exp_data["itemCount"] * 0.5


def _get_gross_rates(exp_data):
    duration = exp_data["time"]
    if duration <= 0:
        raise ValueError(f"Invalid expedition duration: {duration}")

    return {
        "fuel": exp_data["fuel"] / duration,
        "ammo": exp_data["ammo"] / duration,
        "steel": exp_data["steel"] / duration,
        "bauxite": exp_data["baux"] / duration,
        "bucket": _get_item_expected_count(exp_data, "bucket") / duration,
        "devmat": _get_item_expected_count(exp_data, "devmat") / duration,
    }


def _get_reference_consumption_rates(exp_data):
    duration = exp_data["time"]
    if duration <= 0:
        raise ValueError(f"Invalid expedition duration: {duration}")

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


def _get_coefficients(expeditions):
    gross_rates = {
        exp_data["id"]: _get_gross_rates(exp_data) for exp_data in expeditions
    }
    best_gross_rates = {
        resource: max(
            (rates[resource] for rates in gross_rates.values()), default=0.0
        )
        for resource in RESOURCE_NAMES
    }

    coefficients = {}
    for exp_data in expeditions:
        exp_id = exp_data["id"]
        net_rates = dict(gross_rates[exp_id])
        fuel_cost_rate, ammo_cost_rate = _get_reference_consumption_rates(exp_data)
        net_rates["fuel"] -= fuel_cost_rate
        net_rates["ammo"] -= ammo_cost_rate

        # C[e,r] = netRate[e,r] / bestGrossRate[r]
        #
        # Fuel/Ammo cost is subtracted in the numerator while the denominator
        # remains the common gross-production frontier for that resource.
        coefficients[exp_id] = {
            resource: (
                net_rates[resource] / best_gross_rates[resource]
                if best_gross_rates[resource] > 0
                else 0.0
            )
            for resource in RESOURCE_NAMES
        }

    return coefficients


def _get_resource_state(current, desire):
    active = tuple(
        resource for resource in RESOURCE_NAMES if desire[resource] > 0
    )
    if not active:
        raise ValueError("At least one expedition resource desire must be positive")

    # x_r = min(1, current_r / desire_r)
    # H_r = 1 - x_r
    fill = {
        resource: min(1.0, max(0.0, current[resource] / desire[resource]))
        for resource in active
    }
    headroom = {resource: 1.0 - fill[resource] for resource in active}
    # R_r = GM(x_s, s != r, x_s > 0)
    # lag_r = max(0, 1 - x_r / R_r)
    #
    # Ignore zero-valued peers when building the peer reference so a
    # partial-zero boundary does not erase relative balance information
    # among the remaining positive resources.
    positive_fill = {
        resource: value for resource, value in fill.items() if value > 0
    }
    lag = {}
    for resource in active:
        peers = [
            value
            for peer, value in positive_fill.items()
            if peer != resource
        ]
        if not peers:
            lag[resource] = 0.0
        elif fill[resource] == 0:
            # A zero resource lags any positive peer maximally.
            lag[resource] = 1.0
        else:
            peer_reference = _geometric_mean(peers)
            lag[resource] = max(
                0.0, 1.0 - fill[resource] / peer_reference
            )

    return _ResourceState(
        active=active,
        headroom=headroom,
        lag=lag,
        # F = GM(x_r). F weights target completion against relative balance.
        overall_fill=_geometric_mean(fill.values()),
    )


def rank_expeditions(expeditions, current, desire):
    """Rank a pre-filtered auto-expedition candidate pool.

    For expedition e:

        U_e = sum_r H_r * C[e,r]
        B_e = sum_r lag_r * C[e,r]
        Score_e = F * U_e + (1 - F) * B_e

    H_r = 1 - x_r is the remaining-target weight for resource r.
    lag_r is the relative-balance weight for a resource behind its peers.
    F = GM(x_r) is overall fill: low F emphasizes balance, while high F
    emphasizes finishing the remaining configured targets.

    Expanding the score:

        Score_e
          = F * sum_r H_r C[e,r]
            + (1 - F) * sum_r lag_r C[e,r]
          = sum_r [F H_r + (1 - F) lag_r] C[e,r]

    Therefore each resource has one state-dependent ranking weight:

        W_r = F(1 - x_r) + (1 - F)lag_r
        Score_e = sum_r W_r C[e,r]

    Geometric mean becomes zero when any active resource is zero. At all-zero,
    there is no relative imbalance, so ranking uses U. At partial-zero, F = 0
    makes the general formula reduce to B, with U only as an exact-score
    tie-break.
    """
    expeditions = tuple(expeditions)
    if not expeditions:
        return []

    coefficients = _get_coefficients(expeditions)
    state = _get_resource_state(current, desire)
    rows = []

    for exp_data in expeditions:
        exp_id = exp_data["id"]
        coefficient = coefficients[exp_id]
        completion_utility = sum(
            state.headroom[resource] * coefficient[resource]
            for resource in state.active
        )
        balance_utility = sum(
            state.lag[resource] * coefficient[resource]
            for resource in state.active
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
