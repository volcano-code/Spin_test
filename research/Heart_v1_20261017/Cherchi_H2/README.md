# Heart H2 fail-closed export diagnosis

Read-only forensics of H1's actual Cherchi exact-rational output and native floating boundary rejection. H1 evidence is in sibling `../Cherchi_H1/`.

```bash
python source/audit_float_export_failure.py \
 --material ../Cherchi_H1/output_proxy_v1/cherchi-authoritative-exact.json \
 --binary-audit ../Cherchi_H1/evidence/proxy-cherchi-full-audit.json \
 --rational-audit ../Cherchi_H1/evidence/rational-output-audit.json \
 --out evidence/float-failure-diagnosis.json
python -m pytest -q tests
```

No repaired mesh is created. A native exact boundary audit and a global rational-chain equivalence proof are required before any OBJ release.
