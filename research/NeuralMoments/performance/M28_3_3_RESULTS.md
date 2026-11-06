# W1 M28.3.3 — exact cut-segment extraction prototype

Date: 2026-11-06. Parent: `249db334303b31b8b8c2cfcb415b21a7cc2c9464`.

Added a standalone Fraction-based exact non-coplanar triangle intersection segment extractor. Degenerate and coplanar pairs fail closed. Five synthetic tests pass. This is only a cut-segment extraction kernel: no real cut-face batch replay, no full PSLG, no coplanar arrangement, no region classification/coverage comparison, no global Boolean completeness certification. No new Cherchi Boolean or Newton. `production_admitted=false`; `full_solver_speedup=null`.

Next: exact segment noding and PSLG, including coplanar operand patches, then small real cut-face batch.