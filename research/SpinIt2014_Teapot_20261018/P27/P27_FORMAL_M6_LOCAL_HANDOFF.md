# P27 — Formal M6 host handoff

P25 (Run 42178859911) has now demonstrated that the fixed W0 exact-rational repair allows the unchanged W0 native audit to return a complete **TEST_ONLY** represented-set partition. P26 (Run 42180376807) refreshed the P20/P21 source pins and passed 74 P20 plus 72 P21 tests with no skips.

The remaining hard blocker is the formal host resource gate. The standard GitHub runner used by P25 reported 15.61 GiB physical RAM and 3 GiB host swap. It cannot run formal M6. Formal P20/P21 requires at least 20 GiB physical and effective memory, with host swap zero.

The previously reported local machine had 60 GiB RAM and zero swap. If that remains current, it is the preferred existing host; run the preflight below before spending time on a native build. The Docker container is deliberately limited to 24 GiB with zero container swap, so P20 observes a 24 GiB effective limit while retaining the host's physical-RAM and host-swap checks.

## 1. Prepare checkouts

Use three independent clones (not Git worktrees). The Core checkout is mounted read-write for its pinned submodule/dependency preparation, while W4 and W0 are mounted read-only inside the container; separate `.git` directories prevent submodule updates from trying to write through the read-only W4 mount.

```bash
export P27_BASE="$HOME/Spin_test-W4-P27"
mkdir -p "$P27_BASE"

git clone --no-checkout https://github.com/volcano-code/Spin_test.git "$P27_BASE/repo-w4"
git -C "$P27_BASE/repo-w4" fetch origin research/neuralmoments-w4-teapot-p1-20261019
git -C "$P27_BASE/repo-w4" checkout --detach origin/research/neuralmoments-w4-teapot-p1-20261019

git clone --no-checkout https://github.com/volcano-code/Spin_test.git "$P27_BASE/repo-w0"
git -C "$P27_BASE/repo-w0" fetch origin 5bab2eb2616df306906a6887a273f68acfa49320
git -C "$P27_BASE/repo-w0" checkout --detach 5bab2eb2616df306906a6887a273f68acfa49320

git clone --no-checkout https://github.com/volcano-code/Spin_test.git "$P27_BASE/repo-core"
git -C "$P27_BASE/repo-core" fetch origin 58fd12c1306c1c01679a19172e276eef0cb30542
git -C "$P27_BASE/repo-core" checkout --detach 58fd12c1306c1c01679a19172e276eef0cb30542

export W4_ROOT="$P27_BASE/repo-w4"
export W0_ROOT="$P27_BASE/repo-w0"
export CORE_ROOT="$P27_BASE/repo-core"
export P27_ROOT="$P27_BASE/runs"
mkdir -p "$P27_ROOT"
```

The W4 checkout must contain the P26-updated P20/P21 files. The W0 and Core worktrees are pinned to the exact commits above.

## 2. Install Docker if needed

On Ubuntu, if Docker is not installed:

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo docker version
sudo docker info
```

You may use `docker` without `sudo` after adding the account to the docker group and starting a new login session. The scripts automatically try `docker` first and then `sudo docker`.

## 3. Prepare native modules, M/F/D, and an independently reviewable lock

```bash
chmod +x "$W4_ROOT/research/SpinIt2014_Teapot_20261018/P27/p27_prepare_formal_m6.sh"
"$W4_ROOT/research/SpinIt2014_Teapot_20261018/P27/p27_prepare_formal_m6.sh"
```

This step:
- checks host physical RAM and host swap before building;
- builds the pinned Core and original Cherchi modules in Ubuntu 24.04;
- runs the bounded P20 M/F/D preparation and creates a fresh six-pin file;
- runs P21 resource preflight and read-only registration;
- stops before formal M6 geometry execution;
- prints the SHA-256 of `P21_PRERUN_LOCK.json`.

The lock is explicitly not independent attestation and does not grant scientific admission. Review the JSON and register its digest separately (for example, send the exact digest for independent review). Do not edit the lock or its pinned inputs after registration.

## 4. Execute formal M6 only after independent lock registration

After the lock digest has been independently recorded, set it exactly:

```bash
export P27_LOCK_SHA256="<the independently registered 64-character SHA-256>"
chmod +x "$W4_ROOT/research/SpinIt2014_Teapot_20261018/P27/p27_execute_formal_m6.sh"
"$W4_ROOT/research/SpinIt2014_Teapot_20261018/P27/p27_execute_formal_m6.sh"
```

The execution script verifies the external lock digest, rechecks the host and cgroup resource policy, then runs the unchanged P21 same-call capture/replay path. It writes a new, non-overwriting evidence directory under `$P27_ROOT`.

## 5. Interpretation boundary

A successful formal M6 geometry receipt is still not W0 owner adoption, W2 teacher/training admission, smooth derivative-neighborhood certification, Newton terminal certification, or physical validation. Those require their own independent evidence. The P25 TEST_ONLY pins must never be promoted to the formal lock; P27 creates a new six-pin record from the actual host build.
