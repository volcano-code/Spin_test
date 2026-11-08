# W6 P18: three-seed trained-PINO DensiCrafter material design confirmation

P17 seed 271 proved the first true trained-64³ PINO + DensiCrafter
coupled design. P18 repeats the exact same 64³ design protocol using
the three independent P14 trained PINO checkpoints (seeds 271,277,281)
and three independent sphere geometry IDs.

Each seed:
- Strict load P14 64³ trained PINO, freeze every PINO parameter.
- Generate a distinct analytic P0 sphere occupancy at 64³.
- Derive a 2-voxel fixed shell and interior density design.
- Start rho near one; optimize DensiCrafter mass/COM/contact losses.
- Compare Densi-only, PINO-only, soft joint, and 2%-tolerance
  independent-feasibility joint design.
- 12 Adam updates, lr=.06; no Cherchi or FEM.

Acceptance requires every feasible-joint final state to pass:
trained PINO moment change <=2%, independent hard-cut moment change
<=2%, normalized full-material nine-moment change <=2%, fixed shell
exactly preserved. All seed-specific designs and ledgers are saved.

This is still a small synthetic P0 sphere confirmation, not real CAD,
millimeter wall thickness, structural strength, printability, Cherchi
continuous integration or Newton certification.
