"""Shanghai Metro distance-based fare calculation."""

import math
from numbers import Real


def fare_yuan(distance_m: Real) -> int:
    """Return the fare in yuan for a finite non-negative distance in metres."""
    if isinstance(distance_m, bool) or not isinstance(distance_m, Real) or not math.isfinite(distance_m) or distance_m < 0:
        raise ValueError("distance_m must be a finite non-negative number")
    if distance_m <= 6000:
        return 3
    return 3 + math.ceil((distance_m - 6000) / 10000)
