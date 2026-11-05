# R4.2 quadric events on a closed box

Run `python -m unittest -v` in this directory. The implementation and its nine tests use the Python standard library. For example, `classify_box([-1,0,0,0,1,1,1,0,0,0], [-1,-1,-1], [1,1,1])` finds the unit sphere touching all six faces and gives the exact polynomial range `(-1, 2)`.

The input is one nondegenerate axis-aligned box in the same coordinates as the native coefficient vector. The coefficient convention matches W6's existing `analytic_cut.py` and W0. With order `const,x,y,z,xx,yy,zz,yz,xz,xy`, the final three coefficients contribute `2 c7 yz + 2 c8 xz + 2 c9 xy`. Integers, fractions and exact values of binary64 floats are accepted. No rescaling occurs.

| Status | Meaning on this box |
| --- | --- |
| STRICT_POSITIVE or STRICT_NEGATIVE | The exact extrema put the entire box on one strict side of zero. |
| ZERO_STRATUM_EVENT | The result includes an exact zero with zero tangential gradient on an open face, edge, at a vertex, or in the box interior. A vertex zero is always an event. |
| UNKNOWN | A zero stationary affine set may meet an open stratum. The conservative membership check could not settle the intersection. |
| REGULAR_ZERO_SET | The polynomial attains zero and all intersected open strata have nonvanishing tangential gradient. |

Every result withholds `J_D` and sets `training_admitted=False`. A single-box classification supplies neither cut moments nor a derivative over a coefficient neighborhood. Missing CAD, density boundaries, multiple boxes and native teacher observations remain outside its scope.

## Exact range and conservative events

The 27 open strata comprise the interior, six faces, twelve edges and eight vertices. On each stratum, setting the free-coordinate gradient to zero gives a linear system with rational coefficients. The polynomial is constant on its stationary solution set, so one solution suffices to evaluate its stationary value. A solution in the relative interior gives an exact witness. When the system is rank deficient with zero stationary value and the chosen solution falls outside that stratum, the implementation records uncertainty.

Both global extrema are included in the collected values. At an extremum the tangential gradient on the containing stratum vanishes. If that stationary point lies on a positive-dimensional affine flat, a line along the flat reaches the boundary of the bounded stratum at the same value. Descending in dimension eventually reaches a vertex or a unique stationary point. The resulting range is exact even if membership of a zero stationary flat was left unknown. Predicate decisions concern the supplied numbers only.

## Reproduction and provenance

The tests cover face and edge tangencies with nonzero ambient gradient, a vertex event, an interior cone singularity, an enclosed sphere, the adjacent binary64 values on either side of a sphere-face tangency, an uncertain stationary flat, and an oblique shifted polynomial checked against its independent sum-of-squares form. The range oracle uses 36 newly generated diagonal quadrics, seed 24041, and independent one-dimensional extrema. The previous R4.1 report used the same seed for a separate plane benchmark.

The R4.1 archive recorded SHA-256 `9d01d8711e6f12e1c0ef059a5229eadfb421837d43da74b4884035dbd12e26b9`. At W6 parent `057087a7ae69e99f373b4ae0d5ff667fb39d15bb` the tracked R4.1 directory contains six evidence files. Its historical plane benchmark is Git blob `98d4104c482c4b2b9e95fd4b30b33f6eee8f0921`. Neither the incremental bytes nor the separate R4 parent package were available for this run. This implementation is an independent R4.2 component.
