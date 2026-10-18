"""Filesystem operations exercise real temporary files, not container fixtures."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_filesystem():
    spec = importlib.util.spec_from_file_location('filesystem', ROOT / 'images/mcp/filesystem.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fs = load_filesystem().FilesystemMixin()
        self.fs.workspace = self.root

    def test_write_read_edit_and_no_implicit_overwrite(self):
        self.fs.write_file('a.txt', 'héllo')
        self.assertEqual(self.fs.read_file('a.txt')['text'], 'héllo')
        self.assertRaises(FileExistsError, self.fs.write_file, 'a.txt', 'lost')
        self.fs.edit_file('a.txt', 'héllo', 'world')
        self.assertEqual((self.root / 'a.txt').read_text(), 'world')
        self.assertRaises(ValueError, self.fs.edit_file, 'a.txt', 'missing', 'x')

    def test_directory_copy_move_search_and_explicit_delete(self):
        self.fs.make_directory('design/sub', parents=True)
        self.fs.write_file('design/sub/a.txt', 'abc abc')
        self.fs.copy_path('design', 'copy')
        self.fs.move_path('copy/sub/a.txt', 'copy/sub/b.txt')
        listing = self.fs.list_directory('copy/sub', limit=1)
        self.assertEqual(listing['entries'][0]['name'], 'b.txt')
        self.assertEqual(self.fs.stat_path('copy/sub/b.txt')['size'], 7)
        found = self.fs.search_files('copy', '*.txt')
        self.assertEqual([p['path'] for p in found['matches']], ['sub/b.txt'])
        self.assertRaises(ValueError, self.fs.remove_path, 'copy', recursive=True)
        self.fs.remove_path('copy', recursive=True, confirm=True)
        self.assertFalse((self.root / 'copy').exists())

    def test_binary_pagination_symlinks_and_absolute_container_paths(self):
        self.fs.write_file('binary', 'AP9hYg==', encoding='base64')
        page = self.fs.read_file(str(self.root / 'binary'), limit=2, encoding='base64')
        self.assertEqual(page['text'], 'AP8=')
        self.assertEqual(page['next_offset'], 2)
        self.assertTrue(page['has_more'])
        (self.root / 'link').symlink_to(self.root / 'binary')
        self.assertEqual(self.fs.stat_path('link')['type'], 'symlink')
        self.fs.remove_path('link', confirm=True)
        self.assertTrue((self.root / 'binary').exists())
        for offset, limit in ((-1, 2), (0, 65537), (True, 10)):
            self.assertRaises(ValueError, self.fs.read_file, 'binary', offset, limit)

    def test_pagination_and_destination_protection(self):
        for name in ('a', 'b', 'c'):
            self.fs.write_file(name, name)
        first = self.fs.list_directory('.', limit=2)
        self.assertTrue(first['has_more'])
        self.assertEqual(first['next_offset'], 2)
        self.assertEqual(self.fs.list_directory('.', offset=2)['entries'][0]['name'], 'c')
        self.assertRaises(FileExistsError, self.fs.copy_path, 'a', 'b')
        self.assertRaises(FileExistsError, self.fs.move_path, 'a', 'b')
        self.assertRaises(ValueError, self.fs.remove_path, '/', True, True)
        self.assertRaises(ValueError, self.fs.remove_path, '.', True, True)
        self.assertRaises(ValueError, self.fs.search_files, '.', '*', limit=1001)

    def test_special_file_reads_are_rejected_without_blocking(self):
        import os
        os.mkfifo(self.root / 'fifo')
        self.assertRaises(ValueError, self.fs.read_file, 'fifo')
        self.assertRaises(ValueError, self.fs.write_file, 'fifo', 'x', True)
        self.assertRaises(ValueError, self.fs.edit_file, 'fifo', 'x', 'y')
        self.assertRaises(ValueError, self.fs.copy_path, 'fifo', 'copied')

    def test_edits_preserve_crlf_and_bound_expanded_size(self):
        (self.root / 'a').write_bytes(b'one\r\ntwo\r\n')
        self.fs.edit_file('a', 'one', 'ONE')
        self.assertEqual((self.root / 'a').read_bytes(), b'ONE\r\ntwo\r\n')
        self.fs.write_file('many', 'x' * 1000)
        self.assertRaises(ValueError, self.fs.edit_file, 'many', 'x', 'a' * 2000, True)

    def test_content_limits_and_ambiguous_edits(self):
        self.fs.write_file('a', 'x x')
        self.assertRaises(ValueError, self.fs.edit_file, 'a', 'x', 'y')
        self.fs.edit_file('a', 'x', 'y', replace_all=True)
        self.assertEqual(self.fs.read_file('a')['text'], 'y y')
        self.assertRaises(ValueError, self.fs.write_file, 'big', 'x' * (1024 * 1024 + 1))
        self.assertRaises(ValueError, self.fs.write_file, 'bad', '%%', encoding='base64')


if __name__ == '__main__':
    unittest.main()
