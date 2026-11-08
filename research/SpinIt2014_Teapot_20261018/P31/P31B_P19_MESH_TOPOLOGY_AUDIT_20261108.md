# W4 P31-B — P19 mesh topology and material-boundary audit
Date: 2026-11-08
Repository: volcano-code/Spin_test
Read-only source branch: research/neuralmoments-w4-teapot-p1-20261019
Audit implementation: deterministic parser over the exact OBJ text fetched from the W4 Git branch. No source OBJ was changed.

## Exact input identities
| Role | Repository path | Git blob SHA1 | V | F |
|---|---|---|---:|---:|
| M | P1/P19_material_case/material/M_native.obj | e2651b8a2efcc89fee3e69f9ebb78ddffb8f942e | 4035 | 8070 |
| F | P1/P19_material_case/material/F_native.obj | 180c3ade7c939008b90fa1aaabe82653047b2e6c | 4235 | 8470 |
| D | P1/P19_material_case/material/D_native.obj | 9820f3d73d15a4cdd0c504a0264f934aefd40df1 | 200 | 400 |
| S | P1/P19_material_case/source/shaft-reference.obj | 9fe9f78257c7a90970095f6bb54c5148198a33d1 | 258 | 512 |

## Combinatorial surface audit
All four OBJ meshes have:
- zero boundary edges;
- zero edges with incidence > 2;
- zero same-direction orientation conflicts across two-face edges;
- zero duplicate face records;
- zero degenerate/invalid faces;
- zero unused vertices.

Connected components: M=1, F=2, D=1, S=1.

This establishes closed, consistently oriented two-manifold *edge incidence* for the supplied triangle meshes under the parser's indexed topology. It does **not** establish absence of geometric self-intersections, embeddedness, valid nesting, exact Boolean set equality, or printability.

## Strong material-boundary correspondence found
Comparing triangle coordinate triples (not OBJ vertex indices):
- Every one of M's 8,070 faces occurs in F with the same orientation.
- Every one of D's 400 faces occurs in F with the opposite orientation.
- F's two connected boundary components have signed volumes:
  - outer component: +1.6596798579703191 reference^3
  - inner component: -0.026406299068153123 reference^3
- D signed volume: +0.026406299068153116 reference^3.
- F total signed volume: +1.633273558902166 reference^3.
- M volume: +1.6596798579703191 reference^3.
- `M - F - D` normalized residual: `-3.3446903006429426e-17`.

Interpretation: the supplied F surface is exactly represented by the M outer surface plus the oppositely oriented D inner boundary, and its signed volume is consistent with the cavity subtraction M-D. This is strong boundary-correspondence and algebraic-volume evidence. It is **not** a complete geometric containment or no-self-intersection certificate.

## Shaft S caution — owner review required
S is a separate closed reference mesh with 258 vertices and 512 faces. Exact coordinate comparison against F found:
- shared vertices: 2/258;
- shared faces: 0/512;
- S bounding box: [-0.06,-0.06,0] to [0.06,0.06,1.71].

Therefore S is **not** a literal boundary submesh of F. This does not prove it is outside F: it may be intended as an internal/protected shaft volume. But the statement "S is already included in F" is not established by surface identity. W0 must explicitly certify whether S is geometrically contained in F, intersects the cavity D, overlaps the material boundary, or is only an axis/shaft reference. Do not add S mass again, and do not claim containment until a set-membership test is supplied.

## Bounding boxes
- M/F: [-1.1980000000000002,-0.8,0] to [1.3736000000000002,0.8,1.71].
- D: [-0.19993146499511147,-0.19993146499511147,0.48108063181623884] to [0.19993146499511147,0.19993146499511147,0.8589193681837614].
- S: [-0.06,-0.06,0] to [0.06,0.06,1.71].

D's bounding box lies inside M/F's bounding box, but bbox containment is not solid containment.

## Gate result
- P31-B mesh topology and coordinate-boundary correspondence: **PASS (limited combinatorial/algebraic scope)**.
- Geometric self-intersection/embeddedness: **NOT TESTED**.
- D-in-M solid containment: **NOT CERTIFIED**.
- S-in-F solid containment: **NOT CERTIFIED**.
- W0 physical approval: **NOT ISSUED**.
- W2 Teapot teacher approval: **NOT ISSUED**.
- P30-B native Cherchi calls: **0**.
- Optimization, training, printability and MuJoCo before/after: **NOT ADMITTED / NOT EXECUTED**.

## Required next checks
1. W0 independently run robust triangle-triangle self-intersection and solid containment/Boolean set predicates for M, F, D and S; preserve exact source hashes and tool versions.
2. W0 resolve the shaft semantics and explicitly prove the no-double-counting rule.
3. W0 freeze support/contact geometry and the physical load/material envelope for the new B test article.
4. W2 independently inspect the exact same feature branch and Cherchi source/Boolean/integration/derivative provenance, bound to W0's receipt.
5. Only after both owner receipts and an independent P30-B lock: run the local native 12-point pilot.

## Reproducibility limitation
This audit used a lightweight deterministic OBJ parser executed against GitHub-fetched source text. No external geometry kernel was run, no original OBJ was modified, and no native Cherchi or CGAL Boolean computation was performed. The results should be reproduced by the qualified W0 geometry audit before owner authorization.
