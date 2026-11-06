# W2 M22-P3 · Frozen Heart point-000 Boolean boundary local-semantics audit

**Date:** 2026-11-06  
**Run:** `heart-pilot9-flex-20261105T083338329274558-3159689`  
**Historical source:** H8f workflow `39123384402`, artifact `12135528290`  
**W2 branch:** `research/neuralmoments-w2-teacher-20261019`

## Executive result

**PASS — exact output-face provenance, orientation, two-scale local side semantics, and every input-face-centroid coverage check.** This materially advances M22-P3 beyond the M22-P2 surface-only audit.

**NOT CLAIMED — global exact Boolean set equality.** The audit checks every output face and every original input-face centroid, but does not construct and compare the complete exact planar arrangement cells. A sufficiently small omitted patch that contains no input-face centroid is not ruled out by centroid coverage alone.

Keep `J_D=null`, `split=excluded`, `training_admitted=false`, and training samples at zero.

## 1. Exact operands and coordinate binding

The archived M21 frozen request is byte-bound to the H8f `prepared-request.json` (`request_sha256=1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`). Its variable Boolean call uses:

- Operand A: request `design_vertices` / `design_faces`, 13,122 vertices and 26,244 triangles.
- Operand B: the actual Cherchi-generated `quadric_source_vertices` / `quadric_source_faces` saved in historical point-000, 162 vertices and 320 triangles.
- Operation: `subtraction`, i.e. the intended local set is `Design \ QuadricSource`.

The separate fixed shell is represented by `fixed_shell_moments`; it is not a third operand in this Cherchi Boolean call. The outer model is the frozen reconstructed H8 envelope and coordinate/model context.

The historical point-000 output is in the target frame. It was mapped back to the request model frame using the frozen target axes/origin before operand comparisons. The reconstructed binary64 `variable_vertices_model` binding differs from the exact rational affine result by at most `2.220446049250313e-16`.

Important provenance limitation: the M21 same-call attachment descriptor SHA (`b136cbcc09740915cd70615d73fab3ab2aa0b680cdb823cfed12375bed6c20e8`) differs from the historical point-000 canonical material SHA (`6be4faf58ef2fc31b6a1e6d67e601417150d0b43dbd37104b61565a2ca6708c1`). The exact output boundary, geometry/topology identities and moments match, but the complete same-call serialized object/evaluation-map identity is not recovered. This remains a historical-boundary replay, not a full same-call object replay.

## 2. Exact input-boundary topology

Both Boolean operands have exact indexed edge closure and orientation:

| Operand | Vertices | Faces | Edges | Edge incidence | Signed exact volume |
|---|---:|---:|---:|---|---:|
| Design | 13,122 | 26,244 | 39,366 | Every edge used twice in opposite directions | +1.0998850071299318 |
| Quadric source | 162 | 320 | 480 | Every edge used twice in opposite directions | +1.3881363252327446 |

Both are also reported watertight and winding-consistent by the mesh parser. This is indexed closure/orientation, not an independent self-intersection proof for the Design operand. The Cherchi producer's source-boundary gate ran on the actual Quadric source before the Boolean call; the output boundary separately passed the pinned W1 M26 exact self-intersection audit.

## 3. Every output triangle has exact input provenance

Each of the 16,910 exact output triangles was tested against candidate input faces using an outward-safe spatial broad phase followed by exact rational coplanarity and exact projected barycentric containment of all three output vertices.

| Output-face parent | Count | Required orientation |
|---|---:|---|
| Design input triangle | 16,034 | Same as Design |
| Quadric source input triangle | 876 | Reversed from Quadric source |
| Unmatched | 0 | — |

No output face had multiple parent matches. All 16,034 Design-derived faces have positive orientation agreement; all 876 Quadric-derived faces have negative orientation agreement. Thus all output faces are attributable to the two intended Boolean operands, with the correct difference-boundary orientation.

### Parent-face area accounting

Exact projected-area sums of output child faces were accumulated per input triangle. No parent had an output-area ratio above 1.

| Parent operand | Full area covered | Partial area covered | No output child | Over-covered |
|---|---:|---:|---:|---:|
| Design (26,244) | 14,900 | 696 | 10,648 | 0 |
| Quadric source (320) | 48 | 85 | 187 | 0 |

This accounting is consistent with the output being a triangulated subset of each input surface. It is not, by itself, proof that every selected planar cell is present.

## 4. Exact two-sided local set semantics on every output face

For each output face, the exact rational centroid was displaced along its oriented normal by two distinct offsets (`2^-25` and `2^-27`, after scaling the normal so its largest component has magnitude one). Each side point was classified against both closed input operands using exact rational ray/triangle predicates. The primary ray direction was `(1, 1/7, 1/11)`; no ambiguous edge/vertex hits occurred.

All 16,910 faces passed at both offsets with identical classifications:

| Output face parent | Exterior-side classification (Design, Quadric) | Interior-side classification (Design, Quadric) | Count |
|---|---|---|---:|
| Design | (outside, outside) | (inside, outside) | 16,034 |
| Quadric source | (inside, inside) | (inside, outside) | 876 |

Interpretation: every sampled interior side belongs to `Design \ QuadricSource`; the exterior side leaves that set through the appropriate operand boundary. Across both offsets this is 135,280 exact point-in-solid membership checks, with zero ambiguous classifications and zero semantic mismatches.

## 5. Coverage consistency at every original input-face centroid

Each original input triangle centroid was independently classified against the other operand and checked for coverage by an output child triangle belonging to that same parent face.

- Design: 26,244/26,244 centroids classified; 15,245 lie outside the Quadric source and are covered by output; 10,999 lie inside the Quadric source and are not covered.
- Quadric source: 320/320 centroids classified; 99 lie inside Design and are covered by output; 221 lie outside Design and are not covered.
- Ambiguous classifications: 0.
- Expected-versus-observed coverage mismatches: 0.

This checks all original input-face centroids, including faces whose output coverage is partial. It is stronger than checking a handful of visual sample points, but it is still a finite centroid test, not a complete exact arrangement-cell coverage proof.

## 6. Binding to M21/M22 evidence

- M21 raw archive SHA-256: `259b9f288b629415bafa42e4e09d6503e4f474e0e2253e6cc9eb1cd775a64dfd`.
- H8f original archive SHA-256: `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`.
- Point-000 material member SHA-256: `c372f749bf7b85015e2dcdad4a445aeab4f2f6fbd25d622089ec58d471992973`.
- M21 spec SHA-256: `4d3cb03ee3a1190142638a99cd90e6aaf0a3e7030b956ef813ebabeb0c6898d0`.
- M21 label SHA-256: `747101c819d95959020a39ea54eec5af280fd465b786c3f94312bb7447136729`.
- M21 result SHA-256: `f84b38c326bc4fd79068d5a89f94500bb60306c5a77289a550a278355dd89dc3`.
- Exact output boundary SHA-256: `48aae36777ed15e705f1ab919edac07756d3a7444100c060ee5baabd310afe20`.
- Historical point-000 geometry hash: `8dc39e92b09f4c3f00f4415ed1a3f9e6673d4e04ae80723330e04b681b2b5ba0`.
- Historical point-000 topology hash: `efcd3c0975ff434b6a10121da5fd304ca80f00908cb58cb1b0eb15aadffded02`.

Historical point-000 `r_D` exactly matches the M21 label's ten binary64 variable moments; `r_F` matches; `r_total = r_D + r_F` matches. M22-P2 independently reintegrated all ten exact rational moments from the same boundary. No Cherchi call was rerun in M22-P3.

## 7. Remaining scientific blockers

1. **Global Boolean set equality:** still needs an exact arrangement-cell coverage proof or an independent exact Boolean backend comparison. Current output-face provenance, local side semantics, parent area accounting and input-face-centroid coverage do not prove every selected patch is present.
2. **Design operand embedding:** exact edge closure/orientation is verified, but a full exact self-intersection audit of the Design input has not been run here.
3. **Full same-call material provenance:** M21 serialized material payload and native `.so` binaries remain unavailable; historical canonical material SHA and evaluation-map identity differ even though boundary and moments match.
4. **Author CAD provenance:** H8f is explicitly classified as paper-inspired reconstructed CAD, not author-original CAD.
5. **Derivatives and optimization:** `J_D=null`, derivative status remains UNKNOWN, no W0/W3 smooth-neighborhood certification, no Newton acceptance, and no training admission.

## Verdict

**M22-P3 local Boolean boundary semantics: PASS. Global exact set equivalence: NOT YET CERTIFIED.** This is a substantive, source-bound diagnostic improvement. Preserve the M21/H8f historical records unchanged and keep all data excluded.