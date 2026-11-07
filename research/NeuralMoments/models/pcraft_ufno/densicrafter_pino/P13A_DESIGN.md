# W6 P13a DensiCrafter × P-CRAFT Spin-PINO true differentiable data-path integration

**Source audit:** https://github.com/idvxlab/DensiCrafter at
`21e6d8dc646129a9b21a38c2d5bee5bef2704d98`.
MIT license retained in third_party/DENSICRAFTER_LICENSE.

## Why it belongs in the same system
DensiCrafter is NOT another PINO/neural operator architecture.
It optimizes material `rho(x)` and design variables; PINO predicts
a distinct function `r_D(c),J_model(c)`. These are complementary and
can be *fully coupled* via a differentiable density-to-PINO geometry
interface, while preserving PINO as the only core neural operator.

## Original code reused vs adapted
Original MIT DensiCrafter functions:
- `loss.py:mass_penalty` mass regularizer;
- `physical.py:compute_mass_center` density-weighted center;
- `geometry.py:get_smooth_bottom_contact_region` soft floor contact.
These three small primitives are extracted under third_party,
license/commit pinned, with tensor-compatible float exponent.
The original 64³ CUDA-global TRELLIS pipeline, global config,
NumPy/Scipy topology/marching cubes, and periodic torch.roll
neighborhood detection are NOT imported into the PINO core.

New `bridge.py`: arbitrary N>=8 cube volume, fixed outer protected
shell, learnable interior density logits, optional zero-padded 3D
smoothing, physical [-1,1] coordinate grid and selected gravity axis.
It assembles canonical [B,4,X,Y,Z] PINO material input, calls the
unchanged P-CRAFT PINO main U-FNO encoder and original r/J heads, and
backpropagates from cut-moment alignment to density logits. A separate
full-material discrete raw 10-moment ledger verifies mass/moments.
Densi original COM/contact and mass losses join PINO moment alignment
in one differentiable design objective. Model J wrt c is **diagnostic**
and NOT a native Cherchi/ Newton-certifiable J_D. The gradient wrt
density logits is a distinct gradient and does not imply J_D validity.

## Acceptance and actual limitations
- CPU tests: shell cells remain exactly 1, no density outside allowed
  design, gradients reach all valid design cells, coordinate/axis
  invariance of Densi losses, boundary nonwrap, mass ledger, 7-step
  trainable density objective decreases, incorrect inputs rejected.
- This is a **source-code-level functional integration**, not a full
  DensiCrafter generative pipeline, not a 512³ CUDA model, not full
  multi-objective printed STL/GLB reconstruction or FEM/PINN strength.
- Full original TRELLIS/Blender/MuJoCo generation/render/printing remains
  separate because those are different dependencies and workloads, but
  their geometric density output can feed this newly shared interface.
- To make production default, validate robust stress/contact support,
  outer surface at CAD mesh fidelity, world-unit densities,
  variable-cell center quadrature, proper wall thickness & manufacturability,
  full dense/sparse resolution, W0/W2 formally admitted teacher plus
  Cherchi native solver results. The present model only validates
  differentiable **sampled voxel** consistency.

## Cloud vs local
Current cloud GitHub Actions: 8³/16³ CPU, autograd & finite differences,
integration tests and safe data design. User's local GPU: true 512³
sparse/fVDB, TRELLIS generation, Densi printable objects, MuJoCo
videos and genuine Cherchi/Spin-it Faster native convergence.
