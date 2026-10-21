# W0 M18 — W5 v2 compatible, no-release migration proposal

*Frozen W5 original blob:* `14b2ab225a032188fe16570414ef321af9a81e00`.
*Frozen W0 validation blob:* `fe5f71e7cb2b6c6ad45f48c49ab4042f797a113e`.
*W2 current format:* `w2-cherchi-teacher-v2-pre-w0`.

This proposal contains the **complete modified W5 contract_gate.py** under
`research/NeuralMoments/contracts/migration_proposals/w5_contract_gate_v2_m18.py`.
It is deliberately in W0's allowed scope, **NOT installed on W5 branch**.
The W5 owner can review and copy it to
`research/NeuralMoments/models/deeponet/contract_gate.py` **from a W5 checkout**,
then run W5's full existing tests and cross-window CI before announcing migration.

Changes:
1. Unit-c structural tolerance tightened from 1e-9 to exactly 1e-12 in both
   W0 record and W2 legacy candidate checks.
2. Added explicit `inspect_w2_v2_excluded_record` with externally pinned SHA,
   raw ten-dimensional c, legacy q alias, polynomial_q=Bc, fixed F policy,
   topology status, and excluded/undefined J checks.
3. The old `admit_w2_record` refuses W2 v2 as a formal teacher; this is a
   deliberate **lack of release**, not support for actual native training.
4. No W0 v1 schema relaxation, no silent normalization of the 64/81 nonunit
   historical coefficients, no new native Cherchi evaluation and no Newton
   certification. Existing v1 importer remains for legacy source compatibility.

W0 can currently **test this candidate** against the exact frozen W5 source
and its own formal validator through
`test_w5_contract_gate_v2_m18.py`; this does not establish W5 branch adoption.
Until W5 HEAD contains the owner-reviewed changes and new source pin,
`W5_V2_MIGRATION_APPLIED=false` and `training_admitted=false`.

W2 manifest still has zero formally released training/derivative labels.
A future real release requires independent native material + differentiable
neighborhood + terminal evidence and separate approval, not this parser.
