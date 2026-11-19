# Release 0.3.2

## Changelog

### Fixed

- Keep PDK selection banners on stderr so `BASH_ENV` does not contaminate
  non-interactive shell stdout or Make `$(shell ...)` results.
- Restore the Windows VcXsrv startup defaults: `-multiwindow`, clipboard/primary
  selection, WGL, and `LIBGL_ALWAYS_INDIRECT=1` in new containers.
- Start VcXsrv automatically from `start.bat`, or from WSL X11 launchers when
  WSLg is not active. Preserve native Linux, WSLg, VNC and shell-only behavior.
- Avoid Linux X11 socket mounts for TCP display connections.

### Added

- `openpyxl>=3.1` and `cocotb>=2.0,<3` in `/opt/eda-venv`, with runtime import,
  version and executable checks.
- Private, persistent Xauthority generation for automatic VcXsrv startup;
  access control remains enabled. Existing differently configured X servers
  require explicit user closure rather than being killed by the launcher.
- Tests for clean Bash startup, Windows defaults/overrides, WSLg isolation,
  dry-run side effects and Xauthority creation/reuse.

### Documentation

- Define stable wafer.space GF/precheck activation paths, their private PDK
  roots, pinned LibreLane selection and writable precheck working directories.
- Document non-root project virtual environments and gdstk 1.x installation.
- Document `AC3E_XSERVER` and VcXsrv-specific indirect-GL overrides.

### Compatibility

- Preserve all existing tool, template and PDK source pins.
- Retain global gdstk 0.9.x compatibility: glayout 0.0.9 pins gdsfactory 7.7.0,
  which requires `gdstk<1`. Projects requiring `gdstk>=1.0` must use the documented
  independent project venv. KLayout's embedded Python/PCell environment is unchanged.
- Existing containers retain their original image/environment. Accept the
  launcher's version-update prompt or recreate explicitly after preserving needed
  internal files; bind-mounted designs remain persistent.

## Validation and remaining gates

- Host Python tests, Bash syntax, manifest-aware Docker checks and diff checks
  are run before pushing the release branch.
- A focused overlay on image 0.3.1 verified openpyxl 3.1.5, cocotb 2.1.0,
  dependency consistency, Excel round-trip, clean startup stdout for both PDKs,
  and non-root project package installation (including gdstk 1.0.2).
- The generated Xauthority cookie was accepted by a real Xvfb server; an invalid
  cookie was rejected. Windows process boundaries are tested with local fixtures.
- Windows VcXsrv GUI behavior, popup stacking and KLayout rendering performance
  still require validation on Windows. Restoring settings is not proof that all
  reported GUI symptoms are fixed.
- This is not a complete source-image rebuild or full EDA-flow validation.
  Pushing `release/0.3.2` triggers the repository's build/test/publication workflow;
  publication is successful only after that workflow completes.
