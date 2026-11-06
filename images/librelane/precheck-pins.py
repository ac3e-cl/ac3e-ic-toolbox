#!/usr/bin/env python3
"""Validate manifest GF precheck pins, then its own immutable source/lock."""
import json
from pathlib import Path
import re
import sys


def validate(manifest, source=None):
    entries = json.loads(Path(manifest).read_text())['librelanePrechecks']
    if set(entries) != {'gf'}:
        raise ValueError('Expected only GF precheck pins')
    pins = entries['gf']
    for field in ('commit', 'librelaneCommit', 'pdkCommit', 'cielCommit'):
        if not re.fullmatch(r'[0-9a-f]{40}', pins[field]):
            raise ValueError(f'Invalid precheck {field}')
    for field in ('url', 'version', 'pdk', 'cielVersion'):
        if not isinstance(pins[field], str) or not pins[field] or re.search(r'\s', pins[field]):
            raise ValueError(f'Invalid precheck {field}')
    if pins['pdk'] != 'gf180mcuD' or pins['version'] != '1.7.4' or pins['cielVersion'] != '3.1.0':
        raise ValueError('Only GF180MCU-D precheck 1.7.4 / Ciel 3.1.0 is supported')
    if source is not None:
        source = Path(source)
        nodes = json.loads((source / 'flake.lock').read_text())['nodes']
        ciel = nodes[nodes['librelane']['inputs']['ciel']]
        if nodes['librelane']['locked']['rev'] != pins['librelaneCommit']:
            raise ValueError('Precheck LibreLane lock mismatch')
        if ciel['locked']['rev'] != pins['cielCommit'] or ciel['original']['ref'] != pins['cielVersion']:
            raise ValueError('Precheck Ciel lock mismatch')
        match = re.search(r'^PDK_COMMIT\s*\?=\s*([0-9a-f]{40})\s*$',
                          (source / 'Makefile').read_text(), re.M)
        if match is None or match[1] != pins['pdkCommit']:
            raise ValueError('Precheck PDK pin mismatch')
    return '\t'.join(pins[field] for field in
                     ('url', 'commit', 'librelaneCommit', 'pdkCommit', 'cielVersion', 'cielCommit'))


if __name__ == '__main__':
    try:
        if len(sys.argv) not in (2, 3):
            raise ValueError('Usage: precheck-pins.py MANIFEST [SOURCE]')
        print(validate(*sys.argv[1:]))
    except (KeyError, TypeError, ValueError, OSError) as error:
        sys.exit(f'Invalid GF precheck pins: {error}')
