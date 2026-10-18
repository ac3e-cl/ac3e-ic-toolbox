"""ac3e-ic-toolbox stdio MCP (mcp==1.30.0, Python >=3.10).

Jobs belong to this server session: EOF/shutdown cancels process groups. Output
files persist under workspace/.ac3e-ic-toolbox-mcp/<uuid>, not resumable job state.
Scripts/netlists/config and the runtime environment are trusted executable input,
not sandboxed: they can access the container. Path checks constrain API paths,
not EDA scripts' behavior. Never expose this service to untrusted clients.
"""
import argparse
import importlib.util
import os
import re
import select
import signal
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Fixed shell program only: user input is passed as positional arguments.
RUN = ('config=$1; selected=$2; shift 2; source "$config" >&2 || exit $?; '
       'if [[ -n "$selected" ]]; then set_pdk "$selected" >&2 || exit $?; fi; exec "$@"')
LOG_CAP = 8 * 1024 * 1024




def _load_sibling(name):
    # The launcher uses Python -I; do not add workspace directories to sys.path.
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


filesystem = _load_sibling('filesystem')
eda = _load_sibling('eda')
TOOLS = eda.TOOLS


class Backend(filesystem.FilesystemMixin, eda.EDAMixin):
    def __init__(self, workspace='/foss/designs', config='/opt/ac3e-ic-toolbox/config/ac3e-ic-toolbox-env.sh', pdk_root='/opt/pdks'):
        self.workspace = Path(workspace).resolve(strict=True)
        self.config = Path(config).resolve(strict=True)
        self.pdk_root = Path(pdk_root).resolve(strict=True)
        if not self.workspace.is_dir() or not self.pdk_root.is_dir() or not self.config.is_file():
            raise ValueError('workspace/PDK root must be directories and config a file')
        self.output_root = self.workspace / '.ac3e-ic-toolbox-mcp'
        self._check_output_root()
        self.jobs = {}
        self.lock = threading.RLock()
        self.closed = False
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='eda')

    def _check_output_root(self):
        if self.output_root.is_symlink() or self.output_root.resolve() != self.output_root:
            raise ValueError('unsafe output root symlink')
        if self.output_root.exists() and not self.output_root.is_dir():
            raise ValueError('output root must be a directory')

    def input_path(self, path):
        candidate = Path(path)
        if '..' in candidate.parts:
            raise ValueError('path traversal is forbidden')
        resolved = (self.workspace / candidate).resolve()
        if not resolved.is_relative_to(self.workspace) or resolved.is_relative_to(self.workspace / '.ac3e-ic-toolbox-mcp'):
            raise ValueError('input must be inside workspace, outside job outputs')
        if not resolved.is_file():
            raise ValueError('input must be a file')
        return resolved

    def validate_pdk(self, pdk):
        if not isinstance(pdk, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', pdk):
            raise ValueError('invalid PDK name')
        path = (self.pdk_root / pdk).resolve(strict=True)
        if not path.is_relative_to(self.pdk_root) or not path.is_dir():
            raise ValueError('PDK must be a directory within PDK root')
        return pdk

    def list_pdks(self):
        result = []
        for path in self.pdk_root.iterdir():
            try:
                result.append(self.validate_pdk(path.name))
            except (ValueError, OSError):
                pass
        return sorted(result)

    def environment_status(self) -> dict:
        """Report paths, installed PDK names and tool availability, never environment secrets."""
        environment = os.environ.copy()
        environment.pop('BASH_ENV', None)
        environment.update(PDK_ROOT=str(self.pdk_root), DESIGNS=str(self.workspace))
        probe = 'source "$1" >&2 || exit $?; shift; for tool in "$@"; do command -v "$tool" >/dev/null && printf "%s\\n" "$tool"; done; exit 0'
        process = subprocess.Popen(['env', '-u', 'BASH_ENV', 'bash', '--noprofile', '--norc',
                                    '-c', probe, 'ac3e-ic-toolbox-probe', str(self.config), *TOOLS],
                                   env=environment, cwd=self.workspace, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            output, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            self._kill_group(process)
            process.communicate()
            raise RuntimeError('environment inspection timed out') from None
        finally:
            self._kill_group(process)
        if process.returncode != 0:
            raise RuntimeError('runtime configuration failed during environment inspection')
        available = set(output.decode('utf-8', errors='replace').splitlines())
        return {'workspace': str(self.workspace), 'config': str(self.config),
                'pdk_root': str(self.pdk_root), 'pdks': self.list_pdks(),
                'tools': {tool: tool in available for tool in TOOLS},
                'job_lifetime': 'session; shutdown cancels jobs; outputs persist'}

    def simulate_netlist(self, netlist: str, simulator: str = 'ngspice', pdk: str = '', timeout: float = 300) -> dict:
        """Execute a trusted netlist; simulator must be ngspice or Xyce."""
        path = str(self.input_path(netlist))
        if simulator == 'ngspice':
            argv = ['ngspice', '-b', path]
        elif simulator == 'Xyce':
            argv = ['Xyce', path, '-o', 'simulation']
        else:
            raise ValueError('simulator must be ngspice or Xyce')
        return self._submit(argv, pdk, timeout)

    def run_script(self, tool: str, script: str, pdk: str = '', timeout: float = 300) -> dict:
        """Run a TRUSTED EDA script, not a sandbox or turnkey DRC/LVS service.

        Allowed tools: yosys (.ys), openroad (Tcl), klayout (Python/Ruby), magic (Tcl).
        Scripts may execute commands or access container files; client must be trusted.
        """
        path = str(self.input_path(script))
        commands = {'yosys': ['yosys', '-s', path],
                    'openroad': ['openroad', '-exit', path],
                    'klayout': ['klayout', '-b', '-r', path],
                    'magic': ['magic', '-dnull', '-noconsole', path]}
        if tool not in commands:
            raise ValueError('tool must be yosys, openroad, klayout or magic')
        return self._submit(commands[tool], pdk, timeout)

    def start_flow(self, config: str, pdk: str, timeout: float = 3600) -> dict:
        """Run a trusted LibreLane configuration with an explicit installed manual PDK.

        The isolated job directory is the design directory. Use absolute workspace
        paths for sources/includes in the configuration; outputs go into runs/mcp.
        """
        path = str(self.input_path(config))
        self.validate_pdk(pdk)
        return self._submit(['librelane', '--manual-pdk', '--pdk-root', str(self.pdk_root),
                             '--pdk', pdk, '--jobs', '2', '--run-tag', 'mcp', '--design-dir', '.', path], pdk, timeout)

    def run_command(self, argv: list[str], cwd: str = '', pdk: str = '', timeout: float = 300) -> dict:
        """Execute arbitrary Linux argv inside the container, without shell expansion.

        TRUSTED CLIENTS ONLY: full user permissions including mounted host volumes.
        Empty cwd uses an isolated job directory; relative cwd is workspace-relative.
        Logs/artifacts remain in output_dir even when cwd is customized.
        """
        return self._submit(argv, pdk, timeout, cwd=cwd or None)

    def run_shell(self, script: str, cwd: str = '', pdk: str = '', timeout: float = 300) -> dict:
        """Execute a trusted Bash program with pipelines, redirections and Linux utilities.

        This is unrestricted execution, not a sandbox or an approval mechanism.
        Noninteractive only; background descendants are killed when the job finishes.
        """
        if not isinstance(script, str) or not script.strip() or len(script) > 131072 or '\x00' in script:
            raise ValueError('script must be nonempty, NUL-free and at most 128KiB characters')
        return self._submit(['bash', '--noprofile', '--norc', '-o', 'pipefail', '-c', script],
                            pdk, timeout, cwd=cwd or None)

    def list_jobs(self, offset: int = 0, limit: int = 100) -> dict:
        """List jobs in submission order for this session, including their working directories."""
        self._page(offset, limit, 1000)
        with self.lock:
            keys = list(self.jobs)
            entries = [self.job_status(key) for key in keys[offset:offset + limit]]
            return {'jobs': entries, 'next_offset': offset + len(entries),
                    'has_more': offset + len(entries) < len(keys)}

    def _submit(self, argv, pdk, timeout, cwd=None):
        if (not isinstance(argv, list) or not argv or not argv[0] or len(argv) > 4096
                or any(not isinstance(arg, str) or '\x00' in arg for arg in argv)
                or sum(len(arg.encode('utf-8')) + 1 for arg in argv) > 262144):
            raise ValueError('argv must be a nonempty list of NUL-free strings, at most 4096 arguments/256KiB')
        directory_cwd = None
        if cwd is not None:
            directory_cwd = self.filesystem_path(str(cwd)).resolve()
            if not directory_cwd.is_dir():
                raise ValueError('cwd must be an existing container directory')
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 86400:
            raise ValueError('timeout must be between 0 and 86400 seconds')
        if pdk:
            self.validate_pdk(pdk)
        with self.lock:
            if self.closed:
                raise RuntimeError('server is shutting down')
            if sum(j['state'] in ('queued', 'running') for j in self.jobs.values()) >= 2:
                raise RuntimeError('concurrency limit reached (2 jobs); retry later')
            self._check_output_root()
            self.output_root.mkdir(mode=0o700, exist_ok=True)
            job_id = str(uuid.uuid4())
            directory = self.output_root / job_id
            directory.mkdir(mode=0o700)
            job = {'job_id': job_id, 'state': 'queued', 'returncode': None,
                   'output_dir': str(directory), 'process': None, 'cancel': False,
                   'cwd': str(directory_cwd or directory),
                   'error': None, 'log_truncated': False}
            self.jobs[job_id] = job
            self.executor.submit(self._execute, job, argv, pdk, timeout)
            return self.job_status(job_id)

    @staticmethod
    def _kill_group(process):
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _execute(self, job, argv, pdk, timeout):
        process = None
        reader = None
        stop_reader = threading.Event()
        try:
            environment = os.environ.copy()
            environment.pop('BASH_ENV', None)
            environment.update(PDK_ROOT=str(self.pdk_root), DESIGNS=str(self.workspace))
            if pdk:
                environment['PDK'] = pdk
                environment.pop('STD_CELL_LIBRARY', None)
            with self.lock:
                if job['cancel']:
                    job['state'] = 'cancelled'
                    return
                process = subprocess.Popen(
                    ['env', '-u', 'BASH_ENV', 'bash', '--noprofile', '--norc', '-c',
                     RUN, 'ac3e-ic-toolbox-mcp', str(self.config), pdk, *argv],
                    cwd=job['cwd'], env=environment, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
                job['process'] = process
                job['state'] = 'running'
            reader_errors = []
            def drain():
                written = 0
                try:
                    with process.stdout, open(Path(job['output_dir']) / 'output.log', 'wb') as log:
                        while not stop_reader.is_set():
                            if not select.select([process.stdout], [], [], 0.1)[0]:
                                continue
                            chunk = os.read(process.stdout.fileno(), 8192)
                            if not chunk:
                                break
                            remaining = max(0, LOG_CAP - written)
                            log.write(chunk[:remaining])
                            log.flush()
                            written += len(chunk[:remaining])
                            if len(chunk) > remaining:
                                job['log_truncated'] = True
                except Exception as exc:  # noqa: BLE001 - propagate reader failures to the worker.
                    reader_errors.append(exc)
                    # A stopped drain can block the child on a full pipe indefinitely.
                    self._kill_group(process)
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            timed_out = False
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                self._kill_group(process)
                code = process.wait()
            # Kill descendants even when their leader exited normally.
            self._kill_group(process)
            reader.join(timeout=1)
            if reader.is_alive():
                # A trusted command may detach into another session while retaining
                # stdout. Such daemons are outside our process group, not resumable jobs.
                job['log_truncated'] = True
                stop_reader.set()
                reader.join()
            with self.lock:
                job['returncode'] = code
                if reader_errors:
                    job['error'] = str(reader_errors[0])
                job['state'] = ('cancelled' if job['cancel'] else 'failed' if reader_errors
                                else 'timed_out' if timed_out else 'succeeded' if code == 0 else 'failed')
        except Exception as exc:  # noqa: BLE001 - every worker failure must clean up children and mark its job failed.
            self._kill_group(process)
            if process is not None:
                process.wait()
            if reader is not None:
                stop_reader.set()
                reader.join()
            with self.lock:
                job['error'] = str(exc)
                job['state'] = 'cancelled' if job['cancel'] else 'failed'

    def _job(self, job_id):
        if job_id not in self.jobs:
            raise ValueError('unknown job in this session')
        return self.jobs[job_id]

    def job_status(self, job_id: str) -> dict:
        """Inspect a job owned by this MCP session."""
        with self.lock:
            job = self._job(job_id)
            return {key: job[key] for key in ('job_id', 'state', 'returncode', 'output_dir', 'cwd', 'error', 'log_truncated')}

    def cancel_job(self, job_id: str) -> dict:
        """Cancel the entire process group, including surviving children."""
        with self.lock:
            job = self._job(job_id)
            if job['state'] in ('queued', 'running'):
                job['cancel'] = True
                self._kill_group(job['process'])
            return self.job_status(job_id)

    def _artifact(self, job_id, path):
        self._check_output_root()
        root = Path(self._job(job_id)['output_dir'])
        if root.is_symlink():
            raise ValueError('unsafe job directory')
        part = Path(path)
        if part.is_absolute() or '..' in part.parts:
            raise ValueError('artifact path must be relative without traversal')
        target = (root / part).resolve()
        if not target.is_relative_to(root):
            raise ValueError('artifact symlink escapes job directory')
        if not target.is_file():
            raise ValueError('artifact is not a regular file')
        return target

    @staticmethod
    def _page(offset, limit, maximum):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= maximum:
            raise ValueError('invalid pagination bounds')

    def read_artifact(self, job_id: str, path: str, offset: int = 0, limit: int = 65536) -> dict:
        """Read at most 64KiB; offset/next_offset are bytes; UTF-8 uses replacement."""
        self._page(offset, limit, 65536)
        target = self._artifact(job_id, path)
        with target.open('rb') as stream:
            stream.seek(offset)
            data = stream.read(limit)
            more = bool(stream.read(1))
        return {'text': data.decode('utf-8', errors='replace'), 'offset': offset,
                'next_offset': offset + len(data), 'has_more': more}

    def job_logs(self, job_id: str, offset: int = 0, limit: int = 65536) -> dict:
        """Read combined output log, capped at 8MiB on disk, in byte pages."""
        self._page(offset, limit, 65536)
        job = self._job(job_id)
        if not (Path(job['output_dir']) / 'output.log').exists():
            return {'text': '', 'offset': offset, 'next_offset': offset, 'has_more': False}
        return self.read_artifact(job_id, 'output.log', offset, limit)

    def list_artifacts(self, job_id: str, offset: int = 0, limit: int = 100) -> dict:
        """List regular output files without following directory symlinks; paginated."""
        self._page(offset, limit, 1000)
        if offset > 100000:
            raise ValueError('artifact offset exceeds 100000')
        self._check_output_root()
        root = Path(self._job(job_id)['output_dir'])
        if root.is_symlink():
            raise ValueError('unsafe job directory')
        result = []
        seen = 0
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
            for name in sorted(files):
                path = str((Path(directory) / name).relative_to(root))
                try:
                    target = self._artifact(job_id, path)
                except ValueError:
                    continue
                if seen >= offset:
                    if len(result) == limit:
                        return {'artifacts': result, 'next_offset': seen, 'has_more': True}
                    result.append({'path': path, 'size': target.stat().st_size})
                seen += 1
        return {'artifacts': result, 'next_offset': seen, 'has_more': False}

    def close(self):
        with self.lock:
            self.closed = True
            for job_id in self.jobs:
                self.cancel_job(job_id)
        self.executor.shutdown(wait=True)


def create_server(manager):
    """Lazy import keeps host unittest discovery independent of the pinned SDK."""
    from mcp.server.fastmcp import FastMCP
    server = FastMCP('ac3e-ic-toolbox EDA', instructions=(
        'Trusted local clients only. Scripts/config/netlists are executable, not sandboxed. '
        'Jobs are session-owned; disconnect cancels jobs; output files persist. '
        'At most two jobs at once; script runners are not turnkey DRC/LVS. '
        'Filesystem and Linux tools access the entire container with the server user permissions, '
        'including mounted host volumes. Relative filesystem paths use the workspace.'))
    for name in ('environment_status', 'list_pdks', 'simulate_netlist', 'run_script',
                 'start_flow', 'job_status', 'job_logs', 'cancel_job',
                 'list_artifacts', 'read_artifact', 'run_command', 'run_shell', 'list_jobs',
                 *filesystem.FILESYSTEM_METHODS, *eda.EDA_METHODS):
        server.tool(name=name)(getattr(manager, name))
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='/foss/designs')
    parser.add_argument('--config', default='/opt/ac3e-ic-toolbox/config/ac3e-ic-toolbox-env.sh')
    parser.add_argument('--pdk-root', default='/opt/pdks')
    args = parser.parse_args(argv)
    manager = Backend(args.workspace, args.config, args.pdk_root)
    previous = signal.getsignal(signal.SIGTERM)
    def terminate(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    try:
        create_server(manager).run(transport='stdio')
    finally:
        manager.close()
        signal.signal(signal.SIGTERM, previous)


if __name__ == '__main__':
    main()
