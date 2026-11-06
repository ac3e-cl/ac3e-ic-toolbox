"""Keep Ciel backing private; validate resources and recursive directory links."""
from pathlib import Path
import sys


def check_links(root):
    if not root.is_dir():
        raise RuntimeError(f'missing PDK directory: {root}')
    visited = set()
    def visit(path):
        if path.is_symlink() and not path.exists():
            raise RuntimeError(f'broken PDK link: {path}')
        if path.is_dir():
            identity = path.stat().st_dev, path.stat().st_ino
            if identity in visited:
                return
            visited.add(identity)
            for child in path.iterdir():
                visit(child)
    visit(root)


def hide(root):
    check_links(root / 'gf180mcuD')
    for variant in 'ABC':
        public = root / ('gf180mcu' + variant)
        if public.is_symlink():
            public.unlink()
        elif public.exists():
            raise RuntimeError(f'refusing to delete non-symlink backing: {public}')
    check_links(root / 'gf180mcuD')


# Artifact manifest/families.py at Ciel 3.1.0: --include-libraries all.
REQUIRED_LIBRARIES = (
    'gf180mcu_fd_io', 'gf180mcu_fd_pr', 'gf180mcu_fd_sc_mcu7t5v0',
    'gf180mcu_fd_sc_mcu9t5v0', 'gf180mcu_fd_ip_sram',
    'gf180mcu_osu_sc_gp12t3v3', 'gf180mcu_osu_sc_gp9t3v3',
    'gf180mcu_as_sc_mcu7t3v3', 'gf180mcu_re_efuse', 'gf180mcu_ocd_io',
    'gf180mcu_ocd_ip_sram', 'gf180mcu_ocd_sc_rt12t3v3',
    'gf180mcu_ocd_alpha_small', 'gf180mcu_ocd_alpha_large', 'gf180mcu_ocd_alpha_misc',
)
REQUIRED_RESOURCES = (
    'xschem/xschemrc', 'ngspice/design.ngspice', 'ngspice/sm141064.ngspice',
    'magic/gf180mcuD.magicrc', 'klayout/tech/gf180mcu.lyt',
    'klayout/tech/pymacros/cells/__init__.py',
    'klayout/tech/pymacros/cells/efuse/efuse.gds',
    'klayout/tech/macros/gf180mcu_options.lym',
)


def check_ciel(root, commit):
    family = root / 'ciel/gf180mcu'
    public = root / 'gf180mcuD'
    backing = family / 'versions' / commit / 'gf180mcuD'
    if not public.is_symlink() or public.resolve() != backing.resolve():
        raise RuntimeError(f'GF180 public link does not select Ciel commit {commit}')
    current = family / 'current'
    if not current.is_file() or current.read_text().strip() != commit:
        raise RuntimeError(f'Ciel current version does not match {commit}')
    for resource in REQUIRED_RESOURCES:
        path = public / 'libs.tech' / resource
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f'missing PDK resource: {path}')
    for library in REQUIRED_LIBRARIES:
        if not (public / 'libs.ref' / library).is_dir():
            raise RuntimeError(f'missing PDK library: {library}')
    for variant in 'ABC':
        path = root / ('gf180mcu' + variant)
        if path.exists() or path.is_symlink():
            raise RuntimeError(f'unexpected public PDK variant: {path}')
    check_links(public)


if __name__ == '__main__':
    try:
        action, location, *arguments = sys.argv[1:]
        {'hide': hide, 'links': check_links, 'ciel': check_ciel}[action](Path(location), *arguments)
    except RuntimeError as error:
        sys.exit(str(error))
