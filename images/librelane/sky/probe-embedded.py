"""Run with each tool's embedded Python, not the LibreLane Python 3.11 venv."""
import json
import sys

import click
import rich
import yaml
from yaml import _yaml

version = f'python{sys.version_info.major}.{sys.version_info.minor}'
for package in (click, rich, yaml, _yaml):
    assert version in (package.__file__ or ''), (version, package.__file__)
print(json.dumps({'interpreter': sys.version, 'click': click.__file__,
                  'yaml': yaml.__file__, 'rich': rich.__file__}))
