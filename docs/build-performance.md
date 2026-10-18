# Build performance and diagnostics

Build from the repository root with `make build`. The manifest remains the source
of tool revisions; scheduling changes do not upgrade tools or PDKs.

## Dependency-aware parallelism

BuildKit schedules independent Docker stages concurrently. `FROM` and
`COPY --from` are dependency edges: dependent commands start only when their
inputs are ready. Do not start installation scripts with shell `&` inside a
shared filesystem: they can race on package databases, temporary paths, or
installation prefixes.

The build distinguishes lightweight compiler dependencies from the heavier common
libraries. Independent PDK preparation can proceed in separate stages after
Magic is available. Final assembly waits for all required artifacts.

`MAX_BUILD_JOBS` controls compilation jobs **per stage**, not across the entire
build. Several simultaneous compilations each consume that allowance. Keep a
conservative value on memory-constrained hosts, especially for OpenROAD and
OR-Tools. More CPU threads can make a build slower if it starts swapping.

Nix has its own scheduling: `max-jobs` is the number of derivations built at once,
whereas `cores` controls the allowance within a derivation. Downloading a binary
substitute is not accelerated by increasing compiler jobs.

## Cache and measurement

To bound BuildKit concurrency independently of compiler jobs:

```bash
BUILD_MAX_PARALLELISM=2 MAX_BUILD_JOBS=2 make build
```

This opts into a dedicated Docker-container Buildx builder named
`ac3e-ic-toolbox-p2`; it is reused on subsequent builds. `BUILD_BUILDER` overrides
the name. An existing builder with incompatible settings is rejected rather than
modified. The completed image is loaded into Docker. With neither option set,
the ordinary `docker build` path and its existing cache remain in use.

Console output shows stage starts, cache hits, completion and failures. Full logs
are retained under `build/_build_logs/`; errors show the last 40 lines. For full
live diagnostics use `BUILD_VERBOSE=1 make build`. No whole-image percentage is
invented from unrelated stage counters.

Keep the same builder for repeated builds so its cache can be reused. A new
Docker-container builder has its own cache; the first build there may be slower
than a build using the existing Docker daemon cache. Do not remove caches or
force `NO_CACHE=1` when measuring incremental build performance.

Compare cold and warm builds separately. Record elapsed time, peak memory and
which stages were cached. BuildKit stage counters are local to individual
stages, not a reliable whole-image percentage. Network downloads and final image
export may dominate even when compilers are well parallelized.

The build output keeps the full diagnostic log separate from the concise console
progress. Use that log to investigate download failures, compiler errors or
unexpected rebuilds. A successful image build still requires runtime integration
tests; static Dockerfile checks alone do not verify an EDA installation.
