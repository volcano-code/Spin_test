# Heart H3 exact support plane classification

Historical H1 V4 proxy Cherchi material; read-only diagnostics. Requires Python 3.13 and no CGAL production Boolean.

From this directory:

```bash
python source/classify_support_planes.py \
  --material ../Cherchi_H1/output_proxy_v1/cherchi-authoritative-exact.json \
  --binary-audit ../Cherchi_H1/evidence/proxy-cherchi-full-audit.json \
  --rational-audit ../Cherchi_H1/evidence/rational-output-audit.json \
  --output evidence/support-plane-classification.json
python -m pytest -q tests/test_classification.py
```

Not an output mesh repair. The 78 float clashes include 67 cross-plane pairs; there is no justified export without further equivalence proofs and native revalidation.
