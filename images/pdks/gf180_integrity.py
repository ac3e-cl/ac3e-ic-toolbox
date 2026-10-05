"""Keep Volare backing private; validate links including external directories."""
from pathlib import Path
import sys


def check_links(root):
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


if __name__ == '__main__':
    action, location = sys.argv[1:]
    try:
        {'hide': hide, 'links': check_links}[action](Path(location))
    except RuntimeError as error:
        sys.exit(str(error))
