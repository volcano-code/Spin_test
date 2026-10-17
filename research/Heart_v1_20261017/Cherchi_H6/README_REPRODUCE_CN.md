# Heart H6 / Cherchi actual material Jacobian partial study

This is a **real Cherchi Boolean + moment + Jacobian** 25-evaluation experiment on an archived **Heart V4 proxy**, NOT the original Heart `eval60` mesh and NOT a converged Heart optimization. Original `eval60` SHA-registered configuration and events are missing from earlier transferred archives. This repository deliberately fails closed on those paths.

## Reproducing the frozen V4 *proxy* input

From this directory, run:

```bash
python source/restore_v4_proxy.py --output /tmp/archived-heart-v4-request.json
sha256sum /tmp/archived-heart-v4-request.json
```

Expected SHA-256: `fa0a7eac8046be48fbfac495c7e6e283ebe7033d6242b64997aa28216b5c92f4`.

Use a separately built and SHA-checked native `_make_it_stand` and pinned `_cherchi_core_boolean` (see `H6_STAGE_STATUS.json`), and the matching **Spin_test upstream** `python/make_it_stand` source. Configure `PYTHONPATH` to that project `python` dir, the native build/module dirs and this `source/`. The full material experiment is:

```bash
python source/heart_h6_cherchi_jacobian.py \
 --archived-v4 /tmp/archived-heart-v4-request.json \
 --registered-q input/registered-eval60-coefficients.json \
 --columns 0,4,8 \
 --output /tmp/heart-h6-v4-25points
```

Use `--columns 0,1,2,3,4,5,6,7,8,9` only when ready to attempt **81** real evaluations (not yet qualified). The separate source/Boolean branch discriminator is:

```bash
python source/probe_h6_feature_branches.py \
 --archived-v4 /tmp/archived-heart-v4-request.json \
 --registered-q input/registered-eval60-coefficients.json \
 --directions 0,4,8 \
 --output /tmp/heart-h6-feature-classification.json
```

The GitHub Actions workflow runs only **pure Python** integrity/contract tests (no native certification or solve claim):

```bash
python -m pytest -q tests
```

## Recovering the *actual* frozen eval60 on the original host

If the older research machine still has the excluded run output, use:

```bash
python source/collect_original_eval60.py \
 --run /path/to/heart-certified-formal-seed-1-job-01/output/run \
 --registration input/registered-eval60-coefficients.json \
 --output /tmp/heart-real-eval60-registered.zip
```

It checks the exact SHA-256 of both `configuration.json` and `events.jsonl`; refusing a V4 replacement is intentional. Inspect any private/local paths in this bundle before distributing it. Passing this identity gate alone does **not** grant material/derivative/optimizer convergence.

## Evidence

Read `H6_STAGE_REPORT_CN.md`, `H6_STAGE_STATUS.json` and the two files in `evidence/`. 25 genuine Cherchi full moment/Jacobian calls were numerical-passed in 3/10 parameter directions, but some material feature fingerprints changed, so **neighborhood branch certification is false**, and the original full Heart experiment remains pending.
