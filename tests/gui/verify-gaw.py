#!/usr/bin/env python3
"""Verify Gaw's real file load, displayed data export and waveform rendering."""
import math
import pathlib
import socket
import sys
import time

fixture = pathlib.Path(sys.argv[1]).resolve()
run = pathlib.Path(sys.argv[2]).resolve()
deadline = time.monotonic() + 8
while True:
    try:
        connection = socket.create_connection(("127.0.0.1", 1946), timeout=1)
        break
    except OSError:
        if time.monotonic() >= deadline:
            raise RuntimeError("gaw command server readiness deadline exceeded")
        time.sleep(0.1)
with connection:
    connection.settimeout(3)
    channel = connection.makefile("rwb", buffering=0)
    for command in (
        f"load {fixture} ascii",
        "panel 1",
        "copyvar v(out) p0",
        "color_bg #ffffff",
        f"export_data {run / 'export.dat'} ascii",
        f"export_img {run / 'render.png'} png",
    ):
        channel.write((command + "\n").encode())
        response = channel.readline()
        assert response == b"\n", (command, response)
        print("ack:", command)


def read_trace(path):
    lines = path.read_text().splitlines()
    assert "v(out)" in lines[0], lines[0]
    return [tuple(map(float, line.split())) for line in lines[1:] if line.strip()]

expected = read_trace(fixture)
actual = read_trace(run / "export.dat")
assert len(actual) == len(expected) == 5, actual
for got, want in zip(actual, expected):
    assert len(got) == len(want) == 2, got
    assert all(math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-15)
               for a, b in zip(got, want)), (got, want)
print("Verified displayed v(out): 5 samples, 0..20 ns, levels 0/1.8 V")

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib

image_path = run / "render.png"
deadline = time.monotonic() + 5
while True:
    try:
        image = GdkPixbuf.Pixbuf.new_from_file(str(image_path))
        break
    except GLib.Error as error:
        # Gaw acknowledges export before finishing the file. A nonempty PNG
        # can still be incomplete; require successful decoding, not existence.
        last_error = error
    if time.monotonic() >= deadline:
        raise RuntimeError("gaw asynchronous PNG export deadline exceeded") from last_error
    time.sleep(0.1)
width, height = image.get_width(), image.get_height()
assert width > 100 and height > 50, (width, height)
pixels = image.get_pixels()
channels = image.get_n_channels()
stride = image.get_rowstride()
colors = {bytes(pixels[y * stride + x * channels:y * stride + x * channels + 3])
          for y in range(height) for x in range(width)}
assert len(colors) > 10, "blank or unrendered waveform image"
print(f"Decoded waveform PNG: {width}x{height}, {len(colors)} RGB colors")
