# Artifactory backend benchmarks

This directory contains benchmarks used to ensure the Artifactory backend
does not regress in performance when the underlying client library is
replaced (see `../artifactory-plan.md`).

`benchmark_artifactory.py` only uses the public
`audbackend.backend.Artifactory` API, so the exact same script can be
run against any branch and the numbers are directly comparable. Anything
that needs private internals (e.g. raw REST client timing) belongs in a
separate file.

## Requirements

Credentials for an Artifactory host with permission to create and
delete repositories. The script uses
`audbackend.backend.Artifactory.get_authentication()`, which resolves
credentials in this order:

1. `ARTIFACTORY_USERNAME` / `ARTIFACTORY_API_KEY` env vars, if set.
2. Otherwise, the global config file at
   `~/.artifactory_python.cfg` (or `ARTIFACTORY_CONFIG_FILE` if set).
3. Otherwise, anonymous — which will fail for create/delete.

Optional: override the host (default:
`https://audeering.jfrog.io/artifactory`):

    export BENCHMARK_ARTIFACTORY_HOST=https://...

## Running

Full run (creates and deletes a throwaway repository):

    uv run python benchmark/benchmark_artifactory.py \
        --label main-dohq \
        --runs 5 \
        --output benchmark/results/main-dohq.md

Quick smoke test (small sizes, 2 runs, ~1 min):

    uv run python benchmark/benchmark_artifactory.py \
        --quick --label smoke --output benchmark/results/smoke.md

Useful flags:

- `--runs N` — number of timed iterations per case (default: 5)
- `--sizes 1KB,1MB,50MB` — file sizes for put/get benchmarks
- `--workers 1,6` — num_workers values for get_file
- `--ls-sizes 10,100` — directory sizes for the ls benchmark
- `--skip put_file,get_file,...` — skip specific operations
- `--repository NAME` — reuse an existing repository (not deleted)
- `--keep-repo` — keep the auto-created repository on exit

## Comparing branches

1. Check out the branch with the current implementation (e.g. `main`),
   sync deps (`uv sync`), and run:

        uv run python benchmark/benchmark_artifactory.py \
            --label main-dohq --output benchmark/results/main-dohq.md

2. Check out the branch with the new implementation, sync deps, and run:

        uv run python benchmark/benchmark_artifactory.py \
            --label rest --output benchmark/results/rest.md

3. Compare the two markdown tables. The merge criterion for the
   migration is: **no median time worse than the baseline by more than
   5%** on any case.

Both runs should be done back-to-back against the same host and the
same network location to minimise variance.

## Output

Each run produces two files in `benchmark/results/`:

- `<label>.md` — markdown table, one row per (operation, size,
  num_workers) case with median / stdev / min / max in seconds.
- `<label>.csv` — the same data in CSV for diffing or plotting.
