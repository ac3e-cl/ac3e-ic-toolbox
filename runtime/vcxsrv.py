#!/usr/bin/env python3
"""Prepare private X11 authorization and start VcXsrv on Windows or via WSL."""
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys


def windows_path(path):
    if os.name == 'nt':
        return str(Path(path).resolve())
    return subprocess.check_output(['wslpath', '-w', str(path)], text=True).strip()


def main():
    display = os.environ.get('DISPLAY', 'host.docker.internal:0')
    if display.rsplit(':', 1)[-1] not in ('0', '0.0'):
        raise SystemExit('Automatic VcXsrv startup supports display 0 only; use AC3E_XSERVER=native for an external server.')
    if os.environ.get('XAUTHORITY'):
        authority = Path(os.environ['XAUTHORITY']).resolve()
        if not authority.is_file():
            raise SystemExit('XAUTHORITY must name an existing readable authority file.')
    else:
        directory = Path.home() / '.cache/ac3e-ic-toolbox'
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        authority = directory / 'vcxsrv.xauth'
        # Reuse the cookie so restarting a container does not invalidate the server.
        try:
            fd = os.open(authority, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            if authority.is_symlink() or not authority.is_file():
                raise SystemExit('VcXsrv authority path must be a regular file, not a symlink.')
        else:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(struct.pack('>H', 65535))  # FamilyWild for Docker/WSL TCP.
                for value in (b'', b'0', b'MIT-MAGIC-COOKIE-1', secrets.token_bytes(16)):
                    stream.write(struct.pack('>H', len(value)) + value)
        authority.chmod(0o600)
    script = Path(__file__).with_name('start-vcxsrv.ps1')
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                    '-ExecutionPolicy', 'Bypass', '-File',
                    windows_path(script), '-AuthorityFile', windows_path(authority)],
                   check=True, stdout=sys.stderr)
    print(authority)


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Cannot start VcXsrv: {error}')
