# Waveform functional tests

Run from the repository root, against the GUI-enabled image:

```bash
docker run --rm -v "$PWD/tests:/home/designer/tests" isaiash/ac3e-ic-toolbox:0.1.0 bash /home/designer/tests/gui/test-gtkwave.sh
docker run --rm -v "$PWD/tests:/home/designer/tests" isaiash/ac3e-ic-toolbox:0.1.0 bash /home/designer/tests/gui/test-gaw3-xschem.sh
```

- GTKWave converts the five-transition VCD fixture to FST and back, checks exact signal values/times/timescale, then loads the FST using GTKWave's documented `--exit` loader mode. The loader must exit normally within 15 seconds; timeout is failure.
- Gaw loads the five-sample analog fixture through its command server, plots `v(out)`, exports the displayed data, verifies all samples, and exports/decodes a nonblank PNG. It also verifies the process remains alive and has an X window. Command acknowledgements alone are not sufficient: PNG export is asynchronous, so the test waits with a bounded deadline for its artifact.
- Both use a private headless display: Xvfb when available, otherwise the image's TigerVNC Xvnc with its RFB listener disabled. Neither depends on the host display. EXIT/signal cleanup terminates and reaps only processes started by the test, with bounded SIGTERM/SIGKILL fallback.
- Outputs and logs are under `tests/run/gtkwave/` and `tests/run/gaw3-xschem/`. Fixtures are under `tests/data/gui/`. Dependencies come from the image; the tests do not install packages or change installers.
- Gaw PNG verification uses the image's Python GI/GdkPixbuf bindings. `fst2vcd` requires `--output` for the output filename; its second positional argument is not an output path. Gaw's `-C` argument must be an existing file or directory.
