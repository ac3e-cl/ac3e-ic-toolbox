"""Add the direct std::array dependency missing in CVC v1.1.5's CCircuit.hh."""
from pathlib import Path
import sys


def patch_header(path):
    original = path.read_bytes()
    anchor = b'#include "Cvc.hh"'
    if original.count(anchor) != 1:
        raise ValueError('unexpected CCircuit.hh: expected exactly one Cvc.hh include')
    if b'#include <array>' in original:
        return
    start = original.index(anchor) + len(anchor)
    newline = b'\r\n' if original[start:start + 2] == b'\r\n' else b'\n'
    path.write_bytes(original.replace(anchor, b'#include <array>' + newline + anchor, 1))


if __name__ == '__main__':
    patch_header(Path(sys.argv[1]))
