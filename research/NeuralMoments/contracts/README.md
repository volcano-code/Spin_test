# MomentContractV1 — W0 mathematical interface

Frozen source: `0bcc187b3005478baa586a6d6f450e73811ca342`.
Only W0's `research/NeuralMoments/contracts/` and
`research/ParallelLaunch/` are writable by this window.

## Source inspection and exact native meanings

- `src/spin/QuadricCoefficients.cpp` (frozen blob
  `ae831afe9191f67fb2659f112d1b85a8e2b61581`):
  `c=[a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy]`,
  `beta(x)=a+b·x+x^T A x`. The final three terms in the
  *polynomial* are `2*Ayz*yz+2*Axz*xz+2*Axy*xy`;
  the solver's native c stores matrix entries, not doubled monomial
  coefficients. The same blob is on frozen source and W0 branch.
- `python/make_it_stand/verification/spin_common.py` (blob
  `56c908c138c24fd5b90444bfc508904dead71c61`):
  `r=[M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY]`.
  All cross-moment products are ordinary, *not doubled*.
- `python/make_it_stand/verification/faster_material.py` (blob
  `a3c56a395e98e5c19d5924d1568b4e800e94b4d9`):
  independently integrated design material moments and an immutable
  prepared fixed moment contribution enter the external-moment bridge;
  ambient `moment_jacobian` is `dr_variable/dc_native`, while
  supported tangent mode provides a 10×k directional Jacobian together
  with the native 10×k basis. Do not fabricate ambient columns.

Set `B=diag(1,1,1,1,1,1,1,2,2,2)`; monomial coefficient vector
`q=B c`. For smooth full-ambient continuous retained-halfspace
moment maps only, `Jq=Jc B^-1` may be a symmetric boundary Gram
matrix. `Jc` **must not** be checked for symmetry directly. Tangent,
discrete, contact, topology-changing or undefined derivatives **do not**
meet the full smooth Hessian hypothesis without additional proof.

Unit-norm `c` is part of native serialization, and the saved normalized
vector's bit pattern must not be renormalized. Multiplication by a
strictly positive scalar preserves the represented signed halfspace;
negating c exchanges positive and negative halves and **is not an
allowed projective identification**. Retained side is explicit in
serialized contracts.

## Geometry, frames, and physical moments

A contract binds independent original/F/D geometry SHA-256 identities,
coordinate frame, material density, positive scale, and fixed-moment
cache. `r_total(c)=r_F+r_D(c)` and `J_total=J_D`;
no fixed F recomputation per c and no double addition.

For `x'=Ax+t` and density ratio `rho'/rho`, define
`w=abs(det A)*(rho'/rho)`, with original mass M, first moment L and
symmetric ordinary second moment Q:

- `M'=w M`
- `L'=w(AL+M t)`
- `Q'=w[AQA^T+(AL)t^T+t(AL)^T+M tt^T]`

These are raw mass moments, **not** central covariance or inertia
moments. Original-frame normalizations use `rho_ref*L_ref^3`,
`rho_ref*L_ref^4`, `rho_ref*L_ref^5` for M/L/Q errors.
**No universal 1% error threshold** is defined. Schema validation,
analytic P0 samples or a network prediction do **not** prove valid
geometry, correct Boolean material, derivatives or solver convergence.

## Testing and evidence

```bash
python -m pytest -q research/NeuralMoments/contracts/test_contract_v1.py
```

The committed `test_contract_v1.py` checks the native cross-term
factor 2, C++-equivalent polynomial formula, projective sign,
box quadrature, rotated ellipsoid, density and normalized scale,
quadric pullback, analytic P0 sphere-cap quadrature, analytic Jacobian
finite difference, and conditional `Jc B^-1` symmetry.

W0's isolated extended local working suite returned **15 passed**
with an independently compiled C++ formula sentinel; this is
not a claim that the exact committed GitHub test suite was run, nor
that native production Eigen/Cherchi/CAD code was compiled.
Actual W2 sealed real-mesh `r,J`, geometry and source hashes,
failure states and Newton terminal checks are still required.
