# Third-party notices — W6 P0

- NeuralOperator GINO/UQNO: MIT; upstream commit a6648eeeb60fe0837f2d7d021517a945a159a0c8. Original license is in third_party/NEURALOPERATOR_LICENSE. W6 imports the upstream package at runtime; no NeuralOperator model source is vendored.
- QuadrANN: MIT; upstream commit 111dd611aaeac1fb98c76385706b003ea8ef94be. The safe model-core extraction in third_party/quadrann_core.py preserves the upstream model-layer implementation but excludes the example's import-time training and plotting script. Original license is in third_party/QUADRANN_LICENSE.
- Algoim: custom BSD-style license with an enhancement-grant clause; upstream commit da1d81499608e1d499695d255f0233140b8c81e8. CMake fetches the pinned upstream source at build time. License text is copied to third_party/ALGOIM_LICENSE; do not relabel it as MIT/BSD-3-Clause.

All upstream notices must be retained in redistributed source/binary packages. This notice is an engineering record, not legal advice.
