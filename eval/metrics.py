import math
from collections.abc import Sequence
from dataclasses import dataclass

WILSON_Z = 1.959964


@dataclass(frozen=True)
class Rate:
    hits: int
    total: int
    low: float
    high: float

    @property
    def share(self) -> float:
        return self.hits / self.total if self.total else 0.0


# Wilson score interval at 95%: honest for small samples and for counts of 0.
def wilson(hits: int, total: int) -> Rate:
    if total == 0:
        return Rate(0, 0, 0.0, 0.0)
    share = hits / total
    denominator = 1 + WILSON_Z**2 / total
    centre = (share + WILSON_Z**2 / (2 * total)) / denominator
    margin = WILSON_Z * math.sqrt(share * (1 - share) / total + WILSON_Z**2 / (4 * total**2)) / denominator
    return Rate(hits, total, max(0.0, centre - margin), min(1.0, centre + margin))


# Nearest-rank percentile over the sorted values.
def percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]
