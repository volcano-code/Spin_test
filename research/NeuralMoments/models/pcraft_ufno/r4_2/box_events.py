"""Exact-arithmetic diagnostic for a native quadric on one closed 3D box."""
from fractions import Fraction
from itertools import product
from math import isfinite


def _rational(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError("expected an integer, a finite float, or a Fraction")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("non-finite coordinate or coefficient")
    return Fraction(value)


def _stationary_point(matrix, rhs, preferred):
    """Solve Hx=b exactly; use preferred coordinates for free variables."""
    n = len(rhs)
    rows = [list(row) + [v] for row, v in zip(matrix, rhs)]
    pivots = []
    for col in range(n):
        start = len(pivots)
        pivot = next((i for i in range(start, n) if rows[i][col]), None)
        if pivot is None:
            continue
        rows[start], rows[pivot] = rows[pivot], rows[start]
        rows[start] = [v / rows[start][col] for v in rows[start]]
        for i in range(n):
            if i != start and rows[i][col]:
                rows[i] = [v - rows[i][col] * w for v, w in zip(rows[i], rows[start])]
        pivots.append(col)
    if any(row[-1] for row in rows[len(pivots):]):
        return None, False
    result = list(preferred)
    for i, col in enumerate(pivots):
        result[col] = rows[i][-1] - sum(rows[i][j] * result[j]
                                         for j in range(n) if j != col)
    return result, len(pivots) == n


def classify_box(native_c, lower, upper):
    """Inspect the zero set on each open box stratum; return no derivative.

    Native order is const,x,y,z,xx,yy,zz,yz,xz,xy. Coordinates of witnesses,
    stratum labels and min/max are exact; a float denotes its binary64 value.
    Bad inputs raise ValueError before producing a result.
    """
    c, lo, hi = (tuple(map(_rational, a)) for a in (native_c, lower, upper))
    if len(c) != 10 or len(lo) != 3 or len(hi) != 3 or any(a >= b for a, b in zip(lo, hi)):
        raise ValueError("expected ten native coefficients and three increasing box intervals")
    linear = c[1:4]
    A = ((c[4], c[9], c[8]), (c[9], c[5], c[7]), (c[8], c[7], c[6]))
    midpoint = [(a + b) / 2 for a, b in zip(lo, hi)]
    values, events, unresolved = [], [], []
    # -1 and +1 fix a coordinate to a wall; 0 denotes a free coordinate.
    for walls in product((-1, 0, 1), repeat=3):
        free = [i for i in range(3) if walls[i] == 0]
        fixed = [i for i in range(3) if walls[i] != 0]
        x = [hi[i] if w == 1 else lo[i] for i, w in enumerate(walls)]
        hessian = [[2 * A[i][j] for j in free] for i in free]
        rhs = [-linear[i] - sum(2 * A[i][j] * x[j] for j in fixed) for i in free]
        solution, unique = _stationary_point(hessian, rhs, [midpoint[j] for j in free])
        if solution is None:
            continue
        for i, value in zip(free, solution):
            x[i] = value
        beta = c[0] + sum(x[i] * (linear[i] + sum(A[i][j] * x[j] for j in range(3)))
                          for i in range(3))
        if all(lo[i] < x[i] < hi[i] for i in free):
            values.append(beta)
            if beta == 0:
                events.append({"walls": walls, "point": tuple(x)})
        elif not unique and beta == 0:
            # beta is constant on the entire stationary affine flat. Our chosen
            # solution can miss its intersection with the relative interior.
            unresolved.append(walls)
    low, high = min(values), max(values)  # all eight vertices are included
    if low > 0:
        status = "STRICT_POSITIVE"
    elif high < 0:
        status = "STRICT_NEGATIVE"
    elif events:
        status = "ZERO_STRATUM_EVENT"
    elif unresolved:
        status = "UNKNOWN"
    else:
        status = "REGULAR_ZERO_SET"
    return {"status": status, "range": (low, high), "events": events,
            "unresolved_strata": unresolved, "J_D": None, "training_admitted": False}
