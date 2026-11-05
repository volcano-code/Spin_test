"""Exact relative-interior coverage on one projected rational parent triangle.

Supply ALL opposite-boundary cuts and a strict bool keep(point) derived from
independent solid membership. Output and retained regular regions are compared
cell by cell. Isolated edges/vertices, orientation and segment extraction are
separate obligations. Degenerate triangles and exterior output are rejected.
"""
from fractions import Fraction as Q
from itertools import combinations


def point(p):
    if len(p) != 2 or any(type(v) not in (int, Q) for v in p):
        raise ValueError('expected an exact rational 2D point')
    return tuple(map(Q, p))


def sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def edges(t):
    return zip(t, t[1:] + t[:1])


def triangle(t):
    t = tuple(map(point, t))
    if len(t) != 3 or not cross(sub(t[1], t[0]), sub(t[2], t[0])):
        raise ValueError('invalid triangle')
    return t


def contains(t, p):
    signs = [cross(sub(b, a), sub(p, a)) for a, b in edges(t)]
    return min(signs) >= 0 or max(signs) <= 0


def crossing_x(s, t):
    a, b = s
    c, d = t
    u, v, w = sub(b, a), sub(d, c), sub(c, a)
    det = cross(u, v)
    if det:
        h, k = cross(w, v) / det, cross(w, u) / det
        if 0 < h < 1 and 0 < k < 1:
            return a[0] + h * u[0]
    return None


def audit(parent, cuts, output, keep):
    """Return positive-area cell counts and exact missing, extra, overlap areas.

    Overlap area counts multiply covered locations once. cuts are clipped to
    the parent by the caller. Open slab witnesses avoid every supplied edge.
    Complexity is quadratic in the number of segments before cell iteration.
    """
    parent = triangle(parent)
    output = [triangle(t) for t in output]
    segments = set()
    for a, b in (*edges(parent), *(e for t in output for e in edges(t)), *cuts):
        a, b = point(a), point(b)
        if not contains(parent, a) or not contains(parent, b):
            raise ValueError('segment outside parent')
        if a != b:
            segments.add(tuple(sorted((a, b))))
    events = {p[0] for e in segments for p in e}
    for s, t in combinations(segments, 2):
        x = crossing_x(s, t)
        if x is not None:
            events.add(x)
    xs = sorted(events)
    cells = 0
    total = missing = extra = overlap = Q(0)
    for left, right in zip(xs, xs[1:]):
        x = (left + right) / 2
        ys = sorted({a[1] + (x-a[0])*(b[1]-a[1])/(b[0]-a[0])
                     for a, b in segments if a[0] < x < b[0]})
        for low, high in zip(ys, ys[1:]):
            p = x, (low + high) / 2
            if not contains(parent, p):
                continue
            expected = keep(p)
            if type(expected) is not bool:
                raise ValueError('ambiguous membership')
            count = sum(contains(t, p) for t in output)
            area = (right - left) * (high - low)  # affine slab height
            total += area
            cells += 1
            if expected and not count:
                missing += area
            if not expected and count:
                extra += area
            if count > 1:
                overlap += area
    if total != abs(cross(sub(parent[1], parent[0]), sub(parent[2], parent[0]))) / 2:
        raise ValueError('incomplete parent subdivision')
    return dict(cells=cells, area=total, missing=missing, extra=extra,
                overlap=overlap, passes=not (missing or extra or overlap))
