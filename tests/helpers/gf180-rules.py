#!/usr/bin/env python3
"""Small real-deck regressions; upstream fixtures remain installed, unmodified."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def parse_report(path):
    root = ET.parse(path).getroot()
    categories = root.find('categories')
    if categories is None or not list(categories):
        raise ValueError(f'{path}: report has no rule categories')
    counts = {c.findtext('name'): 0 for c in categories}
    geometry = defaultdict(list)
    for item in root.findall('./items/item'):
        rule = item.findtext('category', '').strip().strip("'")
        if rule not in counts:
            raise ValueError(f'{path}: unknown item category {rule!r}')
        values = [v.text.strip() for v in item.findall('./values/value')
                  if v.text and v.text.strip().startswith(('polygon:', 'edge:', 'edge-pair:'))]
        if not values:
            raise ValueError(f'{path}: marker without geometry')
        counts[rule] += 1
        geometry[(item.findtext('cell', ''), rule)].extend(values)
    return counts, {key: sorted(values) for key, values in geometry.items()}


def check_counts(actual, expected):
    for rule, count in expected.items():
        assert rule in actual, f'{rule}: category absent (not evidence of zero violations)'
        assert actual[rule] == count, f'{rule}: expected {count}, got {actual[rule]}'


def generate(root):
    import klayout.db as db
    cases = []

    def save(name, boxes, deck, expected):
        layout = db.Layout()
        layout.dbu = 0.001
        cell = layout.create_cell('TOP')
        for layer, datatype, box in boxes:
            cell.shapes(layout.layer(layer, datatype)).insert(db.Box(*box))
        path = root / f'{name}.gds'
        layout.write(str(path))
        # Check the serialized fixture, not only in-memory geometry.
        reread = db.Layout()
        reread.read(str(path))
        assert len(reread.top_cells()) == 1 and not reread.top_cell().bbox().empty()
        cases.append((name, path, deck, expected))

    base = [(63, 0, (0, 0, 100000, 100000)),
            (22, 0, (0, 0, 35000, 100000)),
            (22, 0, (65000, 0, 100000, 100000))]
    save('dcf-gap-30um-fail', base, 'density', {'DCF.1a': 1})
    save('dcf-dummy-fill-pass', base + [(22, 4, (35000, 0, 65000, 100000))],
         'density', {'DCF.1a': 0})
    save('dcf-ndmy-exemption-pass', base + [(111, 5, (35000, 0, 65000, 100000))],
         'density', {'DCF.1a': 0})
    save('dcf-gap-19um-pass', [base[0], base[1], (22, 0, (54000, 0, 100000, 100000))],
         'density', {'DCF.1a': 0})
    for length, label, expected in [(299, 'fail', 1), (300, 'boundary-pass', 0), (301, 'pass', 0)]:
        save(f'df-butt-{length}nm-{label}',
             [(22, 0, (0, 0, 1000, 1000)), (32, 0, (0, 0, 1000, 1000)),
              (22, 0, (1000, 0, 2000, length)), (31, 0, (1000, 0, 2000, length))],
             'comp', {'DF.11': expected})
    butted = [(22, 0, (0, 0, 2000, 1000)), (32, 0, (0, 0, 1000, 1000)),
              (31, 0, (1000, 0, 2000, 1000))]
    for rule, xfail, xpass in [('CO.5a', 710, 680), ('CO.5b', 1070, 1100)]:
        for label, x, count in [('fail', xfail, 1), ('boundary-pass', xpass, 0)]:
            save(f'{rule.lower()}-{label}', butted + [(33, 0, (x, 390, x + 220, 610))],
                 'contact', {'CO.5a': count if rule == 'CO.5a' else 0,
                             'CO.5b': count if rule == 'CO.5b' else 0})
        # Same deficient contact overlap, but no opposite implant: rule must not apply.
        opposite = 31 if rule == 'CO.5a' else 32
        save(f'{rule.lower()}-not-butted-pass',
             [b for b in butted if b[0] != opposite] + [(33, 0, (xfail, 390, xfail + 220, 610))],
             'contact', {rule: 0})
    return cases


def filler_cases(root, pdk):
    """Extract just two installed standard cells; do not vendor their GDS."""
    import klayout.db as db
    library = 'gf180mcu_fd_sc_mcu7t5v0'
    source = pdk / 'libs.ref' / library / 'gds' / f'{library}.gds'
    layout = db.Layout()
    layout.read(str(source))
    cases = []
    for suffix in ('fill_1', 'fill_64'):
        cell = layout.cell(f'{library}__{suffix}')
        assert cell is not None, f'{source}: missing {suffix}'
        extracted = db.Layout()
        extracted.dbu = layout.dbu
        extracted.create_cell('TOP').copy_tree(cell)
        path = root / f'filler-{suffix}.gds'
        extracted.write(str(path))
        cases.append((f'filler-{suffix}', path, 'density,comp,contact',
                      {'DCF.1a': 0, 'DF.11': 0, 'CO.5a': 0, 'CO.5b': 0}))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deck', type=Path, default=Path('/opt/pdks/gf180mcuD/libs.tech/klayout/tech/drc/gf180mcu.drc'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise SystemExit('output must be a new empty directory (stale reports forbidden)')
    cases = generate(args.output)
    cases.extend(filler_cases(args.output, args.deck.parents[4]))
    unit = args.deck.parent / 'testing/unit'
    for name in ('comp', 'contact', 'ldnmos', 'ldpmos'):
        cases.append((f'upstream-{name}', unit / f'{name}.gds', name, None))
    results = []
    for name, layout, decks, expected in cases:
        report = args.output / f'{name}.lyrdb'
        command = ['klayout', '-b', '-r', str(args.deck), '-rd', f'input={layout}',
                   '-rd', f'report={report}', '-rd', f'decks={decks}',
                   '-rd', 'variant=D', '-rd', 'run_mode=flat',
                   '-rd', 'threads=1', '-rd', 'workers=1']
        with (args.output / f'{name}.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True,
                           timeout=180, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
        counts, geometry = parse_report(report)
        negative_controls = []
        golden_hash = None
        if expected is not None:
            check_counts(counts, expected)
            # Negative control: real failing report must be rejected by clean oracle.
            for rule, count in expected.items():
                if count:
                    try:
                        check_counts(counts, {rule: 0})
                    except AssertionError as exc:
                        negative_controls.append(str(exc))
                        print(f'RED-CONTROL {name}: clean expectation rejected: {exc}', flush=True)
                    else:
                        raise AssertionError(f'{name}: negative control did not fail')
        else:
            golden = unit / f'{decks}.lyrdb'
            golden_hash = hashlib.sha256(golden.read_bytes()).hexdigest()
            gold_counts, gold_geometry = parse_report(golden)
            assert counts == gold_counts, f'{name}: counts differ: actual={counts}, golden={gold_counts}'
            assert geometry == gold_geometry, f'{name}: marker geometry differs from installed upstream golden'
            assert sum(counts.values()) > 0, f'{name}: vacuous golden fixture'
        result = {'name': name, 'expected': expected, 'counts': counts,
                  'negative_controls': negative_controls,
                  'golden_sha256': golden_hash,
                  'markers': sum(counts.values()), 'layout': str(layout),
                  'layout_sha256': hashlib.sha256(layout.read_bytes()).hexdigest(),
                  'command': command}
        results.append(result)
        (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'PASS {name}: {expected if expected is not None else str(result["markers"]) + " upstream markers match geometry and counts"}', flush=True)
    (args.output / 'provenance.json').write_text(json.dumps({
        'deck': str(args.deck), 'deck_sha256': hashlib.sha256(args.deck.read_bytes()).hexdigest(),
        'rule_files_sha256': {str(p.relative_to(args.deck.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(args.deck.parent.rglob('*.rb'))},
        'klayout': subprocess.check_output(['klayout', '-v'], text=True).strip(),
        'cases': len(results), 'signoff': False}, indent=2) + '\n')
    print(f'PASS {len(results)} real-deck regression cases (not signoff)')


if __name__ == '__main__':
    main()
