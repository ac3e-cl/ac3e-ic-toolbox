"""Explicit container filesystem access for trusted MCP clients (not a sandbox)."""
from pathlib import Path
import fnmatch
import os
import shutil
import stat

FILESYSTEM_METHODS = ('read_file', 'write_file', 'edit_file', 'list_directory',
                      'stat_path', 'make_directory', 'copy_path', 'move_path',
                      'remove_path', 'search_files')
MAX_CONTENT = 1024 * 1024


class FilesystemMixin:
    workspace: Path

    @staticmethod
    def _fs_page(offset, limit):
        if type(offset) is not int or not 0 <= offset <= 100000 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError('offset must be 0..100000; limit must be 1..1000')

    def stat_path(self, path: str) -> dict:
        """Inspect metadata without following the final symlink; permissions are octal."""
        target = self.filesystem_path(path)
        info = target.lstat()
        kind = ('symlink' if stat.S_ISLNK(info.st_mode) else 'directory' if stat.S_ISDIR(info.st_mode)
                else 'file' if stat.S_ISREG(info.st_mode) else 'special')
        result = {'path': str(target), 'name': target.name, 'type': kind, 'size': info.st_size,
                  'mode': oct(stat.S_IMODE(info.st_mode)), 'uid': info.st_uid, 'gid': info.st_gid,
                  'mtime': info.st_mtime}
        if kind == 'symlink':
            result['link_target'] = os.readlink(target)
        return result

    def list_directory(self, path: str = '.', offset: int = 0, limit: int = 100) -> dict:
        """List container entries, including hidden files, sorted by name and paginated."""
        self._fs_page(offset, limit)
        names = sorted(self.filesystem_path(path).iterdir(), key=lambda p: p.name)
        entries = [self.stat_path(str(p)) for p in names[offset:offset + limit]]
        next_offset = offset + len(entries)
        return {'entries': entries, 'next_offset': next_offset, 'has_more': len(names) > next_offset}

    def make_directory(self, path: str, parents: bool = False) -> dict:
        """Create a directory; parents=true permits existing directories."""
        target = self.filesystem_path(path)
        target.mkdir(parents=parents, exist_ok=parents)
        return self.stat_path(path)

    def copy_path(self, source: str, destination: str) -> dict:
        """Copy file/directory, preserving symlinks; never overwrite an existing destination."""
        src, dst = self.filesystem_path(source), self.filesystem_path(destination)
        if dst.exists() or dst.is_symlink():
            raise FileExistsError(str(dst))
        if src.is_symlink():
            dst.symlink_to(os.readlink(src))
        elif src.is_dir():
            if dst.resolve().is_relative_to(src.resolve()):
                raise ValueError('cannot copy a directory into itself')
            shutil.copytree(src, dst, symlinks=True)
        else:
            if not src.is_file():
                raise ValueError('copy source must be a regular file, directory or symlink')
            with src.open('rb') as reader, dst.open('xb') as writer:
                shutil.copyfileobj(reader, writer)
            shutil.copystat(src, dst)
        return self.stat_path(destination)

    def move_path(self, source: str, destination: str) -> dict:
        """Move a container path; never intentionally overwrite an existing destination."""
        src, dst = self.filesystem_path(source), self.filesystem_path(destination)
        if dst.exists() or dst.is_symlink():
            raise FileExistsError(str(dst))
        shutil.move(str(src), str(dst))
        return self.stat_path(destination)

    def remove_path(self, path: str, recursive: bool = False, confirm: bool = False) -> dict:
        """Delete only with confirm=true; directories require recursive=true unless empty.

        Root, workspace and their ancestors are protected. This is not an approval UI.
        """
        target = self.filesystem_path(path)
        if not confirm:
            raise ValueError('deletion requires confirm=true')
        if not target.is_symlink() and self.workspace.resolve().is_relative_to(target.resolve()):
            raise ValueError('cannot remove workspace or its ancestors')
        if target.is_symlink() or not target.is_dir():
            target.unlink()
        elif recursive:
            shutil.rmtree(target)
        else:
            target.rmdir()
        return {'path': str(target), 'removed': True}

    def search_files(self, path: str = '.', pattern: str = '*', offset: int = 0, limit: int = 100) -> dict:
        """Find paths by basename glob, without descending into symlinks; at most 100000 entries.

        Paths are relative to search root. scan_truncated means the scan cap was reached.
        """
        self._fs_page(offset, limit)
        root = self.filesystem_path(path)
        if not root.is_dir():
            raise ValueError('search root must be a directory')
        matches = []
        seen = scanned = 0
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs.sort()
            for name in sorted(dirs + files):
                scanned += 1
                if scanned > 100000:
                    return {'matches': matches, 'next_offset': offset + len(matches),
                            'has_more': False, 'scan_truncated': True}
                if not fnmatch.fnmatchcase(name, pattern):
                    continue
                if seen >= offset:
                    if len(matches) == limit:
                        return {'matches': matches, 'next_offset': seen, 'has_more': True, 'scan_truncated': False}
                    matches.append({'path': str((Path(directory) / name).relative_to(root))})
                seen += 1
        return {'matches': matches, 'next_offset': seen, 'has_more': False, 'scan_truncated': False}

    def filesystem_path(self, path):
        if not isinstance(path, str) or not path or '\x00' in path:
            raise ValueError('path must be a nonempty string without NUL')
        return self.workspace / Path(path)

    def read_file(self, path: str, offset: int = 0, limit: int = 65536, encoding: str = 'utf-8') -> dict:
        """Read a container file in byte pages; UTF-8 text or base64 for binary data."""
        import base64
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 65536:
            raise ValueError('invalid pagination bounds')
        if encoding not in ('utf-8', 'base64'):
            raise ValueError('encoding must be utf-8 or base64')
        target = self.filesystem_path(path)
        if not target.is_file():
            raise ValueError('read_file requires a regular file')
        with target.open('rb') as stream:
            stream.seek(offset)
            data = stream.read(limit)
            more = bool(stream.read(1))
        value = base64.b64encode(data).decode('ascii') if encoding == 'base64' else data.decode('utf-8', errors='replace')
        return {'text': value, 'encoding': encoding, 'offset': offset,
                'next_offset': offset + len(data), 'has_more': more}

    def write_file(self, path: str, content: str, overwrite: bool = False, encoding: str = 'utf-8') -> dict:
        """Create a container file; replacement requires overwrite=true. Parents must exist."""
        import base64
        if not isinstance(content, str) or len(content) > MAX_CONTENT:
            raise ValueError('content exceeds 1MiB character limit')
        if encoding == 'base64':
            data = base64.b64decode(content, validate=True)
        elif encoding == 'utf-8':
            data = content.encode('utf-8')
        else:
            raise ValueError('encoding must be utf-8 or base64')
        if len(data) > MAX_CONTENT:
            raise ValueError('decoded content exceeds 1MiB')
        target = self.filesystem_path(path)
        if (target.exists() or target.is_symlink()) and not target.is_file():
            raise ValueError('write target must be a regular file')
        with target.open('wb' if overwrite else 'xb') as stream:
            stream.write(data)
        return {'path': str(target), 'bytes_written': len(data)}

    def edit_file(self, path: str, old_text: str, new_text: str, replace_all: bool = False) -> dict:
        """Replace exact text in a UTF-8 file; ambiguous matches require replace_all=true."""
        target = self.filesystem_path(path)
        if not target.is_file():
            raise ValueError('edit target must be a regular file')
        if target.stat().st_size > MAX_CONTENT:
            raise ValueError('file exceeds 1MiB edit limit')
        if not old_text or len(new_text.encode('utf-8')) > MAX_CONTENT:
            raise ValueError('old_text must not be empty; replacement limited to 1MiB')
        text = target.read_bytes().decode('utf-8')
        count = text.count(old_text)
        if not count or (count > 1 and not replace_all):
            raise ValueError('expected a unique match, or replace_all=true for multiple matches')
        size = len(text.encode('utf-8')) + count * (len(new_text.encode('utf-8')) - len(old_text.encode('utf-8')))
        if size > MAX_CONTENT:
            raise ValueError('edited content exceeds 1MiB')
        result = text.replace(old_text, new_text)
        self.write_file(path, result, overwrite=True)
        return {'path': str(target), 'replacements': count}
