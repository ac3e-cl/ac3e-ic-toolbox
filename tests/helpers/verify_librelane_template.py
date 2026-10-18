#!/usr/bin/env python3
"""Validate final LibreLane views and cocotb xUnit reports."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def verify(final, reports):
    final = Path(final)
    metrics = json.loads((final / 'metrics.json').read_text())
    assert isinstance(metrics, dict) and metrics, 'missing final metrics'
    gds = [path for path in final.rglob('*.gds') if path.stat().st_size]
    assert gds, 'missing nonempty final GDS'
    count = 0
    assert reports, 'no simulation reports requested'
    for report in reports:
        tree = ET.parse(report)
        tests = list(tree.iter('testcase'))
        assert tests, f'empty simulation report: {report}'
        for test in tests:
            assert test.find('failure') is None, f'failed simulation: {report}'
            assert test.find('error') is None, f'simulation error: {report}'
            assert test.find('skipped') is None, f'skipped simulation: {report}'
        count += len(tests)
    return {'simulation_tests': count, 'metrics': str(final / 'metrics.json'),
            'gds': [{'path': str(path), 'bytes': path.stat().st_size} for path in gds]}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]), indent=2))
