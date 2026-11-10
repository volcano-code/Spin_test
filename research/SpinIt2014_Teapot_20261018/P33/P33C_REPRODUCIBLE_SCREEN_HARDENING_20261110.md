# W4 P33-C — reproducible screen regression hardening
Date: 2026-11-10
Branch: research/neuralmoments-w4-teapot-p1-20261019

## New regression coverage
The P32 floating-point triangle screen now has additional synthetic SAT cases:
- disjoint coplanar triangles;
- overlapping coplanar triangles;
- edge contact;
- parallel separated triangles;
- non-coplanar crossing;
- vertex contact.

It also now checks:
- deterministic repeated output for the frozen source meshes;
- rejection when a copied source OBJ is modified and its pinned Git blob SHA1 no longer matches.

These tests complement the mesh-specific expected pair-count/contact-locus assertions. They do not turn the SAT screen into a robust exact predicate.

## CI artifact retention
The W4 P32 workflow now:
- writes the diagnostic JSON into the GitHub Actions step summary;
- uploads the JSON as a run artifact named with the workflow commit SHA;
- fails if the expected JSON file is missing;
- retains the artifact for 30 days.

## Verified source state
Fetched back from the W4 branch:
- `P32/p32_triangle_screen.py`: blob `9bb85c3a90602a5455f1fa18464b9a9f3168620e`.
- `P32/test_p32_triangle_screen.py`: blob `bd4c9e46a61fa52128734dcb71a72bdd95a7af90`.
- `.github/workflows/w4-p32-triangle-screen.yml`: blob `874f0a1985aa0fd32f5c46520b2d97af47049d57`.

GitHub combined commit-status queries for the test and workflow commits returned empty status lists. Therefore the workflow execution and test pass are **not confirmed** in this report. The commits and file contents are verified, but no green CI is claimed.

## Scientific scope
All output gates remain false for robust solid containment, physical approval, Cherchi native pilot, Newton, training, optimization and printability. This workflow is a reproducible floating-point diagnostic only.

## Current dependencies
- W0 Teapot receipt: missing.
- W2 Teapot receipt: missing.
- Independent robust geometry certificate: missing.
- Contact choice and material/load contract: not frozen.
- Cherchi 12-point pilot: 0 new native calls.
