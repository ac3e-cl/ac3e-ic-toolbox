"""Stdlib-only EDA operations for the trusted, local MCP Backend.

The catalog describes repository intent, NOT measured installation or successful
EDA execution. Inherit EDAMixin alongside the job/filesystem backend. Tool inputs
are executable trusted content; executable allowlisting is not a sandbox.
"""
from copy import deepcopy
from pathlib import Path
from typing import Callable

# Examples are literal argv, not shell commands or synthetic tool wrappers.
_CATALOG = (
    ('gnucap', 'GNU Circuit Analysis Package', ('analog simulation', 'batch command files'), ['gnucap', '-b', '/foss/designs/design.ckt']),
    ('ngspice', 'SPICE circuit simulator', ('analog simulation', 'OSDI models'), ['ngspice', '-b', '/foss/designs/design.cir']),
    ('Xyce', 'Parallel circuit simulator', ('analog simulation',), ['Xyce', '/foss/designs/design.cir', '-o', 'simulation']),
    ('magic', 'VLSI layout editor and Tcl engine', ('layout', 'DRC', 'extraction'), ['magic', '-dnull', '-noconsole', '/foss/designs/layout.tcl']),
    ('openvaf', 'Verilog-A to OSDI compiler', ('compact model compilation',), ['openvaf', '/foss/designs/model.va', '-o', 'model.osdi']),
    ('klayout', 'Layout viewer and scripting engine', ('layout', 'scripted DRC', 'scripted LVS'), ['klayout', '-b', '-r', '/foss/designs/check.py']),
    ('xschem', 'Schematic capture and netlisting', ('schematic', 'headless netlisting', 'Tcl scripts'), ['xschem', '-n', '-q', '-x', '-o', '.', '/foss/designs/design.sch']),
    ('netgen', 'Circuit comparison and LVS', ('LVS', 'Tcl scripts'), ['netgen', '-batch', 'lvs', '/foss/designs/a.spice top', '/foss/designs/b.spice top', 'nosetup', 'lvs.log']),
    ('gaw', 'Analog waveform viewer', ('waveform viewing', 'GUI'), ['gaw', '/foss/designs/wave.raw']),
    ('yosys', 'RTL synthesis and analysis', ('synthesis', 'formal preparation', 'scripts'), ['yosys', '-s', '/foss/designs/synth.ys']),
    ('eqy', 'Yosys equivalence checking frontend', ('formal equivalence',), ['eqy', '-d', 'equivalence', '/foss/designs/check.eqy']),
    ('sby', 'SymbiYosys formal verification frontend', ('formal verification', 'proof', 'cover', 'BMC'), ['sby', '-d', 'formal', '/foss/designs/check.sby']),
    ('mcy', 'Mutation coverage frontend', ('mutation coverage', 'project commands'), ['mcy', 'status']),
    ('cvc_rv', 'Circuit Validity Checker', ('circuit electrical rule checking', 'power and voltage checks'), ['cvc_rv', '/foss/designs/design.cvcrc']),
    ('verilator', 'Verilog/SystemVerilog compiler and linter', ('lint', 'simulation compilation'), ['verilator', '--lint-only', '/foss/designs/design.sv']),
    ('iverilog', 'Icarus Verilog compiler', ('Verilog compilation', 'SystemVerilog subset'), ['iverilog', '-g2012', '-o', 'simulation.vvp', '/foss/designs/testbench.sv']),
    ('vvp', 'Icarus compiled simulation runtime', ('Verilog simulation',), ['vvp', '/foss/designs/simulation.vvp']),
    ('gtkwave', 'Digital waveform viewer', ('waveform viewing', 'GUI'), ['gtkwave', '/foss/designs/wave.vcd']),
    ('openroad', 'RTL-to-GDS physical design engine', ('floorplanning', 'placement', 'routing', 'Tcl scripts'), ['openroad', '-exit', '/foss/designs/design.tcl']),
    ('librelane', 'Automated ASIC implementation flow', ('RTL-to-GDS flow', 'manual PDK'), ['librelane', '--manual-pdk', '--pdk-root', '/opt/pdks', '--pdk', 'sky130A', '--design-dir', '.', '/foss/designs/config.json']),
    ('nix', 'Nix package and development environment manager', ('toolchain environments', 'package management'), ['nix', '--version']),
    ('sta', 'OpenSTA timing analysis command referenced by runtime config', ('static timing analysis', 'Tcl scripts'), ['sta', '-exit', '/foss/designs/timing.tcl']),
)
TOOLS = tuple(entry[0] for entry in _CATALOG)
EDA_METHODS = ('tool_catalog', 'run_tool', 'xschem_netlist', 'netgen_lvs', 'lint_verilog',
               'compile_verilog', 'run_vvp', 'compile_veriloga', 'run_formal', 'run_tool_script')


class EDAMixin:
    # Host backend contract; annotations do not override its implementations.
    input_path: Callable[[str], Path]
    filesystem_path: Callable[[str], Path]
    validate_pdk: Callable[[str], str]
    _submit: Callable[..., dict]

    def run_tool_script(self, tool: str, script: str, pdk: str = '',
                        timeout: float = 300, cwd: str = '') -> dict:
        """Run trusted Netgen/Xschem Tcl, GNUCAP commands or OpenSTA Tcl.

        Complements existing run_script (Yosys/OpenROAD/KLayout/Magic). Script
        code can access the container and run commands; this is not a sandbox.
        """
        commands = {'netgen': ['-batch', 'source'], 'xschem': ['-q', '-x', '--script'],
                    'gnucap': ['-b'], 'sta': ['-exit']}
        if not isinstance(tool, str) or tool not in commands:
            raise ValueError('script tool must be netgen, xschem, gnucap or sta')
        return self.run_tool(tool, [*commands[tool], self._eda_input(script)], pdk, timeout, cwd)

    def run_formal(self, tool: str, config: str = '',
                   arguments: list[str] | None = None, pdk: str = '',
                   timeout: float = 3600, cwd: str = '') -> dict:
        """Run trusted EQY/SBY configurations or MCY project subcommands.

        EQY/SBY write to formal/ under cwd; flags/tasks follow the config as
        literal arguments. Supply cwd for relative project sources. MCY does
        NOT accept an SBY-style config argument: provide an existing project cwd
        (config.mcy) and actual subcommand argv, default ['status']. MCY is
        currently excluded from the image; solvers/engines are not guaranteed.
        Process success alone is not a parsed proof/coverage result.
        """
        self._eda_text(config, 'config')
        options = self._eda_arguments([] if arguments is None else arguments)
        if tool in ('eqy', 'sby'):
            if not config:
                raise ValueError('EQY/SBY require a config file')
            argv = ['-d', 'formal', self._eda_input(config), *options]
        elif tool == 'mcy':
            if config or not cwd:
                raise ValueError('MCY requires project cwd, no config argument')
            argv = options if arguments is not None else ['status']
        else:
            raise ValueError('formal tool must be eqy, sby or mcy')
        return self.run_tool(tool, argv, pdk, timeout, cwd)

    def compile_veriloga(self, source: str, output: str = 'model.osdi',
                         arguments: list[str] | None = None, pdk: str = '',
                         timeout: float = 300, cwd: str = '') -> dict:
        """Compile a trusted Verilog-A file to OSDI with OpenVAF.

        The output filename is local to cwd; extra flags may override defaults.
        This does not load the resulting model into a simulator.
        """
        options = self._eda_arguments([] if arguments is None else arguments)
        return self.run_tool('openvaf', [self._eda_input(source), '-o', self._eda_output(output), *options],
                             pdk, timeout, cwd)

    def run_vvp(self, program: str, arguments: list[str] | None = None,
                pdk: str = '', timeout: float = 300, cwd: str = '') -> dict:
        """Run a trusted compiled Icarus program plus literal runtime/plusargs.

        filesystem_path permits generated artifacts according to backend policy,
        unlike input_path which may exclude job outputs. No automatic job wait.
        """
        self._eda_text(program, 'program')
        path = self.filesystem_path(program)
        if not Path(path).is_file():
            raise ValueError('program must be a file')
        options = self._eda_arguments([] if arguments is None else arguments)
        return self.run_tool('vvp', [str(path), *options], pdk, timeout, cwd)

    @classmethod
    def _eda_output(cls, value: str) -> str:
        cls._eda_text(value, 'output')
        if not value or value in ('.', '..') or '/' in value or '\\' in value or value.startswith('-'):
            raise ValueError('output must be a single filename, not an option or path')
        return value

    def compile_verilog(self, sources: list[str], output: str = 'simulation.vvp',
                        top: str = '', standard: str = '2012',
                        arguments: list[str] | None = None, pdk: str = '',
                        timeout: float = 300, cwd: str = '') -> dict:
        """Compile Icarus sources to a cwd-local VVP program; does not run it.

        Extra literal flags are trusted and may override defaults. Use an
        explicit project cwd to share generated outputs with subsequent jobs.
        """
        if standard not in ('1995', '2001', '2005', '2005-sv', '2009', '2012'):
            raise ValueError('unsupported Icarus language standard')
        self._eda_text(top, 'top')
        argv = ['-g' + standard, '-o', self._eda_output(output)] + (['-s', top] if top else [])
        options = self._eda_arguments([] if arguments is None else arguments)
        return self.run_tool('iverilog', argv + options + self._eda_sources(sources), pdk, timeout, cwd)

    def _eda_sources(self, sources: list[str]) -> list[str]:
        self._eda_arguments(sources)
        if not sources:
            raise ValueError('at least one source file is required')
        return [self._eda_input(source) for source in sources]

    def lint_verilog(self, sources: list[str], top: str = '',
                     arguments: list[str] | None = None, pdk: str = '',
                     timeout: float = 300, cwd: str = '') -> dict:
        """Lint explicit source files with Verilator --lint-only.

        Additional literal arguments may supply include dirs, defines or language
        flags, or override tool behavior. Relative includes need explicit cwd.
        """
        self._eda_text(top, 'top')
        options = self._eda_arguments([] if arguments is None else arguments)
        argv = ['--lint-only'] + (['--top-module', top] if top else [])
        return self.run_tool('verilator', argv + options + self._eda_sources(sources), pdk, timeout, cwd)

    def _eda_input(self, value: str) -> str:
        self._eda_text(value, 'input path')
        return str(self.input_path(value))

    @staticmethod
    def _eda_tcl_word(value: str) -> str:
        # Netgen expects each circuit spec to be a Tcl list (filename, top).
        # Backslash quoting preserves spaces/braces/control characters without
        # evaluating Tcl or constructing a shell command.
        escaped = {'\n': '\\n', '\r': '\\r', '\t': '\\t', '\v': '\\v', '\f': '\\f'}
        return ''.join(escaped.get(char, '\\' + char if char in ' \\{}[]$;"' else char) for char in value)

    def netgen_lvs(self, reference: str, reference_top: str, implementation: str,
                   implementation_top: str, setup: str = '', pdk: str = '',
                   timeout: float = 300, cwd: str = '') -> dict:
        """Run Netgen batch LVS with explicit circuit tops; writes lvs.log.

        setup is a trusted Tcl file or empty for nosetup. Job success means
        process exit zero, NOT an LVS match: inspect lvs.log for comparison.
        """
        specs = []
        for filename, top in ((reference, reference_top), (implementation, implementation_top)):
            self._eda_text(top, 'top')
            if not top:
                raise ValueError('top must not be empty')
            specs.append(self._eda_tcl_word(self._eda_input(filename)) + ' ' + self._eda_tcl_word(top))
        self._eda_text(setup, 'setup')
        return self.run_tool('netgen', ['-batch', 'lvs', *specs,
                             self._eda_input(setup) if setup else 'nosetup', 'lvs.log'], pdk, timeout, cwd)

    def xschem_netlist(self, schematic: str, rcfile: str = '', pdk: str = '',
                      timeout: float = 300, cwd: str = '') -> dict:
        """Headless Xschem netlisting into job cwd (-n -q -x -o .).

        A trusted rcfile controls netlist format, libraries and PDK setup. The
        schematic/rcfile may execute Tcl; this is not schematic validation.
        """
        arguments = ['-n', '-q', '-x', '-o', '.']
        self._eda_text(rcfile, 'rcfile')
        if rcfile:
            arguments += ['--rcfile', self._eda_input(rcfile)]
        return self.run_tool('xschem', arguments + [self._eda_input(schematic)], pdk, timeout, cwd)

    @staticmethod
    def _eda_text(value: str, name: str) -> str:
        if not isinstance(value, str) or '\x00' in value:
            raise ValueError(f'{name} must be a string without NUL')
        try:
            size = len(value.encode('utf-8'))
        except UnicodeEncodeError:
            raise ValueError(f'{name} must be UTF-8 encodable') from None
        if size > 32768:
            raise ValueError(f'{name} exceeds 32768 bytes')
        return value

    @classmethod
    def _eda_arguments(cls, arguments: list[str]) -> list[str]:
        if not isinstance(arguments, list) or len(arguments) > 1024:
            raise ValueError('arguments must be a list of at most 1024 strings')
        result = [cls._eda_text(arg, 'argument') for arg in arguments]
        if sum(len(arg.encode('utf-8')) + 1 for arg in result) > 262144:
            raise ValueError('arguments exceed 262144 bytes including separators')
        return result

    def run_tool(self, tool: str, arguments: list[str], pdk: str = '',
                 timeout: float = 300, cwd: str = '') -> dict:
        """Submit literal argv to an inventoried executable, without shell parsing.

        Inputs/configuration are trusted executable content, not sandboxed. By
        default outputs and relative paths use the isolated job directory. An
        explicit cwd uses filesystem_path's policy and may write into that tree;
        those files are not necessarily job artifacts. Use absolute input paths
        otherwise. Missing optional/excluded tools fail through normal job logs.
        Limits: 1024 arguments, 32KiB UTF-8 each, 256KiB total with separators;
        NUL/non-string arguments and non-finite/invalid timeouts are rejected.
        """
        if not isinstance(tool, str) or tool not in TOOLS:
            raise ValueError('tool must be an exact catalog executable name')
        arguments = self._eda_arguments(arguments)
        self._eda_text(pdk, 'pdk')
        self._eda_text(cwd, 'cwd')
        if type(timeout) not in (int, float) or not 0 < timeout <= 86400:
            raise ValueError('timeout must be between 0 and 86400 seconds')
        if pdk:
            self.validate_pdk(pdk)
        if cwd:
            directory = self.filesystem_path(cwd)
            if not Path(directory).is_dir():
                raise ValueError('cwd must be a directory')
            return self._submit([tool, *arguments], pdk, timeout, cwd=directory)
        return self._submit([tool, *arguments], pdk, timeout)

    def tool_catalog(self) -> dict:
        """Describe all inventoried tools/resources; availability is not probed.

        GUI tools need a display. Xyce and MCY are excluded in the current image;
        STA is a runtime-config reference, not guaranteed installed standalone.
        CLI examples require real user inputs, PDK setup and supporting engines.
        """
        entries = []
        for name, description, capabilities, example in _CATALOG:
            notes = {'mcy': 'Installation disabled in images/yosys/install.sh; inventory exclusion.',
                     'Xyce': 'Excluded from the current final image by tests/exclusions.json.',
                     'sta': 'OPENSTA_EXE=sta in runtime config; standalone binary may be absent.'}.get(name, '')
            entries.append({'name': name, 'description': description,
                            'capabilities': list(capabilities), 'examples': [deepcopy(example)],
                            'status': 'excluded' if name in ('mcy', 'Xyce') else 'optional' if name == 'sta' else 'expected',
                            'available': None, 'notes': notes})
        return {'tools': entries, 'resources': [
            {'name': 'open_pdks', 'description': 'Sky130/gf180 PDK resources, not an executable.'},
            {'name': 'ihp-sg13g2', 'description': 'IHP SG13G2 PDK models and technology resources.'},
            {'name': 'OpenROAD-flow-scripts', 'description': 'ORFS make-based flow resources at ORFS_DIR; inventory does not validate compatibility.',
             'examples': [['make', '-C', '/opt/OpenROAD-flow-scripts/flow', 'DESIGN_CONFIG=/foss/designs/config.mk']]}],
            'trusted_inputs': True,
            'notes': 'No installation probe. Use environment_status for availability; missing executables fail as jobs. Relative inputs resolve in cwd, which defaults to an isolated job output directory. No sandbox; tools/scripts may access the container.'}
