# W6 P25.1c — Short-job sharding for UQNO data collection

## Why

P25.1b's per-seed collection performs 960 geometry/query/resolution rows in
one job. GitHub Actions logs showed runner shutdown signals during the long
collection command for seeds 271/277, while seed 281 completed in an earlier
attempt. The failed jobs did not report a Python exception; the runner
terminated the process and the train-calibrate job was skipped.

The workflow also previously used cancel-in-progress concurrency. That setting
was changed to false so later W6 commits cannot cancel an active calibration
run. To reduce exposure to runner lifetime interruptions, P25.1c now shards
collection by geometry family.

## New job layout

3 matched model seeds x 3 geometry families = 9 collection jobs.

Each shard contains:
- one model seed;
- one family (box, sphere, or ellipsoid);
- 80 unique geometries;
- 2 coefficient queries per geometry;
- 64^3 and 128^3 resolutions;
- 320 geometry/query/resolution rows.

The training job merges three family shards per seed into the original
960-row seed report, then builds 960 ensemble geometry/query/resolution
groups across the three matched model seeds.

## Reproducibility and integrity

- Shared deterministic dataset seed remains 20261108.
- Model seed/checkpoint pairing remains (271,883), (277,887), (281,991).
- Geometry IDs and query indices remain deterministic across resolutions.
- The trainer checks each shard's seed, family and exact row count before
  aggregation.
- Missing shards fail the workflow; partial training is not permitted.

## Limits

This is an execution reliability change, not a model or statistical-method
change. It does not alter training/calibration/test split logic or promote
UQNO to a production gate.
