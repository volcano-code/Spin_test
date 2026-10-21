# W2-M20 — Real 94-part Noodles V7 / six exact CGAL F/D/A seal and replay DAG

Date: 2026-10-21. Repo `volcano-code/Spin_test`, write only `research/neuralmoments-w2-teacher-20261019` under `research/NeuralMoments/teacher/`. Historical CGAL and Cherchi artifacts are immutable; no main/W0/W3 files edited.

## Actual executed results

1. Independently re-opened real original Noodles V7 reconstructed input bundle `W2_M18_Noodles_V7_94_Source_Recovery.zip`, confirming 94 signed, closed source components and all 188 model/SI SHA matches to the original main manifest. This is a **read-only revalidation**, not a repeated rebuild of the 94 meshes. Preserves source corpus SHA `6b2da86949e4426986e2460167f1255f0c44d6e708be87bfec17fb78ce4a69c6`, main input manifest SHA `67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a` and historic CGAL receipt SHA `35f74fbdb432ee4eccebf21d7e4f1f07408f63420c659025857f1d83d15abfd0`.
2. Ran `m20_csg_partition_gate.py` against the authentic bundle. It saved the result and **exited 2** with `BLOCKED_NO_SIX_PINNED_RATIONAL_CSG_PACKET_BYTES`. Original six exact CGAL outputs were not available: `design`, `envelope`, `fixed`, `fixed-inside-envelope`, `fixed-outside-envelope`, `initial`. Old 96 native CGAL operations are only an archived report, **new native CGAL = 0**, Cherchi teacher = 0, J_D = null, training admitted = 0. Current 4 GiB cgroup memory is below the 24 GiB/0 swap research protocol; original compiled `noodles-exact-boolean` and its `common.py` native command adapter are absent.
3. Built and ran `m20_csg_96_replay_plan.py`: the original frozen source recipe deterministically yields **92 source fixed-part union steps + 4 final difference/union/intersection/difference steps**, exactly **96** Boolean ops, with explicit source node dependencies, leaf OBJ SHA and output paths. This is a *plan*, not 96 newly executed CGAL calls. Output `M20_HISTORICAL_96_BOOLEAN_DAG.json` sha256 `922900847e8b1ed3ceac7bf0e4e81a16547671e139ec5956ae1e21a2804ba3b5`.
4. Implemented independent exact rational verification of six future saved boundary packets (SHA/face count pinned out of band, full triangle index and reversed-directed-edge closure, signed positive exact material volume and 10 exact mass moments each). Four required **exact** ten-moment relations:
   - E = D + (F ∩ E)
   - F = (F ∩ E) + (F \\ E)
   - A = E + (F \\ E)
   - A = D + F
   *These are necessary accounting checks, not proof of Boolean semantics, self-intersection freedom, or continuous differentiability.* Exact fractions are required; a float approximated solid cannot substitute. Packet JSON needs precise `vertices` and `faces` arrays; original CGAL packet parser compatibility is **not yet verified**, because original six packets are absent.
5. Ran **27/27 local real-asset/synthetic tests**, 0 skips/failures, 1.526 seconds. Synthetic disjoint unit voxel unions exercise 60 exact moments and 4 additive identities; tampering, wrong orientation, missing packet, forged hash, approximate float coordinates and duplicate index are rejected. Real source tests verify the 94-part ZIP and original receipt. Synthetic voxel tests are **not native Cherchi or native CGAL**.

## Reproduce (from W2 checkout; Python standard library)

```bash
export W2_M18_SOURCE_BUNDLE=/path/to/immutable/W2_M18_Noodles_V7_94_Source_Recovery.zip
python -m unittest discover -s research/NeuralMoments/teacher -p 'test_m20_*.py' -v
python research/NeuralMoments/teacher/m20_csg_partition_gate.py \
  --source-bundle "$W2_M18_SOURCE_BUNDLE" --output /new/path/M20_REAL_94_INPUT_FDA_PREFLIGHT.json
# Exit 2 is the expected real scientific non-admission.
python research/NeuralMoments/teacher/m20_csg_96_replay_plan.py \
  --source-bundle "$W2_M18_SOURCE_BUNDLE" --output /new/path/M20_HISTORICAL_96_BOOLEAN_DAG.json
# Exit 0: source-locked planning succeeded; does not launch a Boolean.
```

For restored six original packet bytes, specify `--csg-dir`; original SHA-256 and face counts from the sealed historic construction receipt must all match. Even after passing six exact F/D/A ten-moment identities, **only an independently authenticated CGAL Boolean/source provenance and continuous/material partition test** can grant geometry admissibility. No W0/W3 permission or teacher training release is inferred.

## Required next native experiment

At a >=24 GiB-effective RAM, swap=0 isolated machine, source-build the specific original CGAL backend or obtain externally attested executable with pinned SHA `d6803f184047f6172b177b9f436b16f22cdb6a949126d1df88a5d084f3dd9df3`; recover the historical `common.py` CLI semantics rather than guessing binary flags. Execute the verified 96-op frozen DAG *serially*, capture rational packets and their own new SHAs; compare to original six SHA and disclose any legitimate version drift. Independently seal F, D, A including embedding and binary64 partition before declaring a Noodles teacher input. Separately run frozen Heart fresh native Cherchi with externally SHA-pinned `make_it_stand`, core Boolean, rational moments and separate ten-reference budgets. W0 and W3 must independently certify Jacobian neighborhood before any training promotion.

**M20 status: source identity and exact-six algebraic receiver completed; historical six packets missing, native CSG/FDA and fresh Cherchi teacher remain blocked.**
