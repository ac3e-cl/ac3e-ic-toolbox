from test_pdk_contract import PdkContract, CONFIG

class ShellEnvironment(PdkContract):
    def test_shared_environment(self):
        designs = self.base / 'designs'
        designs.mkdir()
        (designs / '.designinit').write_text('export PDK=gf180mcuD\nexport HOOK_COUNT=$(( ${HOOK_COUNT:-0} + 1 ))\n')
        r = self.bash(f'''set -eu; before=$PWD; source "{CONFIG}/ac3e-ic-toolbox-env.sh"; old=$PATH; source "{CONFIG}/ac3e-ic-toolbox-env.sh"; test "$PATH" = "$old"; test "$PWD" = "$before"; test "$HOOK_COUNT" = 1; test "$PDK" = gf180mcuD; bash -c 'type sak-pdk; test "$PDK" = gf180mcuD' ''')
        self.assertEqual(r.returncode, 0, r.stderr)
    def test_nix_and_shell_modes(self):
        nix = self.base / '.nix-profile/etc/profile.d'
        nix.mkdir(parents=True)
        (nix / 'nix.sh').write_text('export NIX_TEST=1\n')
        self.env['LD_LIBRARY_PATH'] = '/bad/library'
        for mode in ['-lc', '-ic']:
            r = __import__('subprocess').run(['bash', '--noprofile', '--norc', mode, f'source "{CONFIG}/profile.sh"; type sak-pdk; test "$NIX_TEST" = 1; test -z "${{LD_LIBRARY_PATH+x}}"'], env=self.env, text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
    def test_hook_failure(self):
        designs = self.base / 'designs'
        designs.mkdir()
        (designs / '.designinit').write_text('return 19\n')
        r = self.bash(f'source "{CONFIG}/ac3e-ic-toolbox-env.sh"')
        self.assertEqual(r.returncode, 19, r.stderr)
