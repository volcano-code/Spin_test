# W6 P29 — TRELLIS-driven geometry expansion for Spin-PINO

Status: plan frozen; implementation starts with manifest contracts and CPU validation. No TRELLIS inference or physical labels are claimed by this commit.

## 0. Research decision

P-CRAFT PINO remains the only primary operator for the ten mass moments and their coefficient Jacobian. TRELLIS/TRELLIS.2 are upstream geometry proposal sources only. They do not supply physical labels, do not replace the PINO backbone, and are not part of the inference path.

The intended contribution is not "more generated meshes". It is a controlled study of whether generated and real complex geometry improves geometry-disjoint generalization of a geometry-conditioned PINO, with independent physical truth and uncertainty-aware exact fallback.

## 1. Why expand beyond P25.1

The frozen P25.1 pilot contains Box, Sphere and Ellipsoid only: 80 geometries per family, 240 geometry IDs, two coefficient queries, 64^3 and 128^3. This is a useful analytic/control set but weak coverage of concavity, thin walls, internal cavities, branching, disconnected components and real CAD distributions.

Keep the existing P25.1 data as a regression/control set. Do not replace it.

## 2. Data sources and staged target

P29.1 is a 100-candidate pilot, not a promise that all generated candidates will pass physical validation.

| Source stratum | Candidate count | Examples | Intended role |
|---|---:|---|---|
| TRELLIS v1 image-conditioned | 30 | brackets, housings, impellers, handles, organic solids | first generative baseline |
| TRELLIS.2 image-conditioned | 20 | cavities, thin features, intricate topology, multi-part assets | topology-rich generation |
| Parametric procedural CAD-like | 20 | holes, ribs, fillets, slots, thin walls, branching channels | controlled coverage |
| Public CAD assets | 20 | engineering components with known source/license | real-world distribution |
| Adversarial topology set | 10 | open surfaces, non-manifold, near-zero-thickness, disconnected solids | robustness/OOD only |
| **Total candidates** | **100** | | |

After validation, expected supervised solid set is a subset of these candidates. Do not force the pass count. Keep rejected assets and reasons in a separate robustness manifest. If fewer than 60 valid solids survive, run a second generation/curation batch before teacher labelling.

### Generation protocol

1. Prefer image-conditioned generation for TRELLIS v1 where a reference view can constrain engineering shape. Use TRELLIS.2 as a separate stratum, not a drop-in replacement.
2. Use fixed prompt/reference IDs, generator commit, checkpoint ID, seed, inference config, and source image license in a generation manifest.
3. Generate multiple variants per prompt, but group all variants under one `lineage_id`; all descendants of a prompt/reference/asset must stay in one data split.
4. Do not use texture/PBR appearance as material density. Assign physical density explicitly in the physics manifest.
5. Preserve raw GLB/mesh and hashes. Never overwrite raw generated assets with repaired meshes.

## 3. Geometry validity and two-track policy

Each candidate gets a geometry audit with: mesh hash, units, transform, bounds, component count, watertightness, winding consistency, self-intersection status, positive volume, minimum feature/thickness diagnostics, and repair history.

- **Supervised solid track:** closed, watertight, consistently oriented, non-self-intersecting, positive-volume solid(s), explicit scale and density. Multiple disconnected solids are allowed only when each component is valid and the intended composite semantics are explicit.
- **Robustness/OOD track:** open surfaces, non-manifold meshes, uncertain winding, self-intersections, and near-zero-thickness cases. These are not silently converted to ordinary solid labels. They may be used for parser/voxelizer/OOD stress tests; physical labels require a separately defined surface/shell model.
- Repair must be deterministic, versioned, and recorded as a derived asset with its own hash. Retain original and repaired versions and quantify volume/surface change.

## 4. Physical label contract

For every accepted solid:
- define units and an explicit similarity transform to the canonical coordinate frame;
- define material density in kg/m^3 independently of texture;
- create occupancy/SDF representations at 64^3, 128^3, 256^3; 512^3 is a later resource-gated tier;
- query coefficient vectors from a fixed, versioned design, covering the original range plus boundary/adversarial values;
- obtain continuous ten-moment labels and derivatives from the frozen Cherchi teacher contract when W0/W2 publish the compatible interface;
- obtain independent voxel hard-cut labels as a separate discretization reference;
- verify Jacobians independently by finite differences on a held-out subset;
- never train on PINO predictions as if they were ground truth.

If the exact teacher is unavailable, cloud work may complete geometry parsing, manifest validation, voxelization smoke tests and teacher-input packaging. Do not fabricate Cherchi labels or claim P29.3 complete.

## 5. Dataset design and leakage control

- Split by `lineage_id` first, then by base asset ID. Variants, remeshes, repairs and multiple views from one base asset must remain in one split.
- Stratify by source family and topology class, but reserve at least one geometry subtype or source subgroup as a genuinely unseen test.
- Keep analytic controls in every evaluation report, but report generated/CAD results separately.
- Report counts before and after each filter, failure reasons, volume/bounds distributions, component counts, topology mix and resolution occupancy.
- Publish a dataset card with source licenses and provenance before any paper claim.

## 6. Model experiments (P29.4)

Use identical splits, coefficient queries, optimizer, training budget and compute protocol for:
A. existing P-CRAFT PINO + P25.1 analytic data;
B. same architecture + procedural geometry;
C. same architecture + TRELLIS v1;
D. same architecture + TRELLIS.2;
E. same architecture + CAD;
F. combined sources.

Only after these controlled data ablations, test an encoder change (occupancy/SDF/inside-boundary multi-channel geometry encoder, cached once per geometry). This separates "better data" from "better architecture". Keep P-CRAFT PINO as backbone.

Primary metrics: ten-moment relative error by component, Jacobian relative error and finite-difference agreement, error by topology/source/resolution, calibration and unsafe acceptance, memory, geometry-encoding time, per-query inference time, exact fallback rate, and paired end-to-end speedup.

## 7. Cloud vs local execution

### ChatGPT/GitHub cloud work (can start now)
- freeze this plan, manifests, schemas, validators and CPU CI;
- write deterministic prompt/reference manifests and asset naming;
- build GLB/mesh ingestion interfaces, metadata extraction wrappers and report generation;
- build dataset lineage split checks and leakage tests;
- develop CPU-side unit tests, voxelization interfaces and teacher-input packaging;
- inspect uploaded sample meshes/metadata and review audit reports;
- prepare P29.3 adapters against the W0/W2 frozen teacher contract once available.

### Must run on user's local Ubuntu workstation (no external GPU server assumed)
- download checkpoints and compile TRELLIS CUDA extensions;
- execute TRELLIS/TRELLIS.2 inference and generate the 100 candidates;
- run GPU mesh-to-voxel/O-Voxel conversion and 256^3/512^3 resource tests;
- run local Cherchi/native teacher jobs and large batch labelling;
- run full GPU training and measure 4090 VRAM/throughput.

GitHub Actions is CPU CI only; do not schedule TRELLIS inference there.

## 8. Hardware/deployment gate before local installation

Known workstation context to re-check before installation: RTX 4090 24GB; current CUDA toolkit previously reported as 11.8; storage was previously nearly full (roughly 28GB free on /home and 41GB on /data). Re-run `nvidia-smi`, `nvcc --version`, `df -h`, and `free -h` before installing anything.

- TRELLIS v1 official setup lists at least 16GB VRAM and has tested CUDA 11.8/12.2; it is the lower-risk first deployment candidate.
- TRELLIS.2 official setup lists at least 24GB VRAM and recommends CUDA 12.4. A 24GB 4090 is exactly at the published minimum, with no comfortable headroom for concurrent workloads; treat it as a gated experiment with reduced/offloaded settings, not a guaranteed success.
- Use new isolated environments; never alter the existing Spin/W1/W2/W6 Python environments or system CUDA globally.
- Do not begin multi-gigabyte checkpoint installs until disk headroom and exact cache destinations are checked. Keep HF cache and model weights on /data if space permits.

## 9. Milestones and acceptance gates

| Milestone | Owner/execution | Acceptance |
|---|---|---|
| P29.0 contracts | ChatGPT/GitHub cloud | manifest schema, validator, CI pass |
| P29.1 install smoke | user local 4090 | isolated TRELLIS v1 first; TRELLIS.2 separately gated |
| P29.2 100-candidate generation | user local GPU | 100 raw assets + provenance, no forced pass rate |
| P29.3 geometry audit and voxel packaging | cloud code + local execution | accepted/rejected manifests, deterministic hashes, occupancy at 64/128/256 |
| P29.4 physical teacher labels | local Cherchi/W2 + cloud audit | ten moments, Jacobian, independent voxel labels, FD checks |
| P29.5 data ablation | cloud orchestration + local GPU training | A-F controlled comparisons and lineage-held-out results |
| P29.6 encoder ablation | local GPU + cloud analysis | multi-channel geometry encoder vs current encoder |
| P29.7 high-resolution test | local 4090 | 256^3 then 512^3 memory/time/error evidence |

P29.1 is not complete merely because the package installs. P29.2 is not complete merely because a mesh renders. P29.3 is not complete without topology/scale/density audits. P29.4 is not complete without independent physical truth.

## 10. Immediate next actions

1. Cloud: add and test a strict geometry manifest validator and lineage checks (P29.0).
2. Local: run the read-only hardware/storage preflight commands supplied in the handoff; do not install yet.
3. After preflight: install TRELLIS v1 in a new environment and generate 3 smoke assets; export GLB/mesh and hashes.
4. Only after smoke passes, generate the remaining candidate set in batches.
5. TRELLIS.2 is a second deployment gate after v1, storage cleanup, and CUDA 12.4 isolated-environment feasibility review.

## 11. Non-claims

At this point, no TRELLIS assets have been generated, no TRELLIS checkpoint has been installed, no new Cherchi labels exist, no 256^3/512^3 training has been performed, and no production gate or speedup claim is made.
