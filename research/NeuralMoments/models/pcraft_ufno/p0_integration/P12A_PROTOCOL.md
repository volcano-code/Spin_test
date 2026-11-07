# W6 P12a: repair geometric conditioning of QuadrANN in selected P11 bridge

W6 main PINO stays frozen. P11's original QuadrANN was evaluated at fixed
PINO quadrature nodes; that does not vary with geometry and therefore
cannot be fairly presented as a geometry-dependent proposal.

P12 adds an **opt-in** material-point conditioning:
1. select valid occupied source voxel centers with positive rho*occupancy;
2. apply the exact pinned MIT QuadrANN model to the actual sampled
   geometry-point coordinates (not fixed 64 node positions);
3. carry author-produced positive point weights plus sampled source
   mass through a deterministic RBF to the fixed PINO quadrature nodes;
4. bound the multiplicative positive correction to the original
   support-masked PINO quadrature, which still exclusively computes
   r(c) and diagnostic J_model(c).
This mapping is W6-original engineering, not a copied or certified
quadrature law. Geometry-only weights avoid missing d(weights)/dc.
An invalid tiny support throws rather than inventing geometry.

Existing legacy/default P11 is unchanged:
`quadrann_condition_on_material=False`.
P12 later trains one upstream adapter per run, compares unchanged
PINO and a matched-label-budget baseline, and calibrates UQNO on
disjoint geometry IDs. No Cherchi supervisor, native Newton Jacobian
or 512^3 CUDA admission follows from these tests.
