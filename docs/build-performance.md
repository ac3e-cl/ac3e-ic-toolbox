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

PDK generation is budgeted separately: `PDK_BUILD_JOBS` bounds the jobs of the
volare/open_pdks gf180 build (default 1). Its peak comes from magic converting
large SRAM/IO layouts, not from compiler throughput, so it must not inherit the
compiler allowance.

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

## Memory-bounded release CI

The release workflow does not load the build result into Docker. It uses a
dedicated `docker-container` builder and `BUILD_OUTPUT=registry` to push gzip
layers directly to a unique `ci-<commit>-<run>-<attempt>` tag in the release
repository. This avoids overlapping BuildKit export with Docker image loading;
it does not require buffering a complete image in RAM or writing a Docker tarball.
Candidate tags are visible before testing and are **not releases**. They remain
available for diagnosis; periodically remove old `ci-*` tags using registry
retention tooling, without deleting manifests still referenced by release tags.

CI sets a 10 GiB container memory ceiling and a 12 GiB combined RAM+swap ceiling,
leaving host headroom on the existing runner without adding swap. BuildKit uses
`GOMEMLIMIT=4GiB` and `GOGC=50` to reclaim Go-managed memory earlier. The Go budget
is soft and excludes compiler subprocesses and other non-Go allocations; the
container limit is the hard backstop, not a guarantee that any workload fits.
Solver concurrency and compiler jobs are each limited to two. Two heavy stages
therefore share one memory ceiling: the gf180 PDK stage is not budgeted against
a co-scheduled heavyweight compiler (BuildKit picks the pair, so a PDK build can
sit next to Xyce/Trilinos or OpenROAD). The PDK stage's own jobs are bounded by
`PDK_BUILD_JOBS=1`, and the Go budget is kept well below the ceiling so the
non-Go subprocesses of both stages keep headroom. Gzip level 1
reduces compression work; it is not itself a memory bound. Larger compressed
layers and additional registry traffic are intentional tradeoffs.

After export, CI saves the full build log and digest metadata, removes its
disposable builder (including its cache) to release memory **and disk**, then
pulls the exact digest for integration tests. Only successful tests permit
registry-side promotion to the release tag. Promotion copies the tested manifest
without another layer export, and verifies that the published digest matches.
A failed build/test leaves the release tag unchanged. These controls remove the
previous local-export path; full-image peak memory must still be measured in CI.

Ordinary `make build` and `./build/build-image.sh` are unchanged: output defaults
to `local`, with the existing Docker cache and a runnable local image. Registry
output is explicit and requires both `BUILD_BUILDER` and `BUILD_METADATA_FILE`;
it does not automatically apply CI resource limits to a workstation builder.
