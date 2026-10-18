{
  description = "Isolated Tiny Tapeout SKY LibreLane 3.0.14 / Python 3.11 runtime";
  inputs.librelane.url = "github:librelane/librelane/f24e0ea5db2260719e9a0c7d51d07db74a87fa23";
  outputs = { self, librelane }: let
    systems = [ "x86_64-linux" ];
    forSystems = librelane.inputs.nix-eda.inputs.nixpkgs.lib.genAttrs systems;
  in {
    packages = forSystems (system: let
      pkgs = librelane.legacyPackages.${system};
      # LibreLane 3.0.14 lexically captures its Python 3.11 click/rich/yaml
      # even when wrapping a tool with Python 3.13. Resolve against each tool.
      embeddedPython = tool: pkgs.lib.makeOverridable
        ({ target ? tool }: _ignored:
          (tool.withPythonPackages.override { inherit target; })
            (ps: [ ps.click ps.rich ps.pyyaml ])) { };
      ciel311 = pkgs.python311.pkgs.callPackage (librelane.inputs.ciel + "/default.nix") { flake = librelane.inputs.ciel; };
      # Upstream's Python binding rebuilds the entire Qt application for 3.11.
      # Use the exact support-tools wheel, as a Nix derivation (not pip LibreLane).
      klayout311 = pkgs.python311.pkgs.buildPythonPackage {
        pname = "klayout";
        version = "0.29.12";
        format = "wheel";
        src = pkgs.fetchurl {
          url = "https://files.pythonhosted.org/packages/85/69/0e307c2cf1c52410112618eb2020b91efa43066e076130510a103be992c8/klayout-0.29.12-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl";
          sha256 = "b0e8ce8eca4885d41721a6a9e46ba7d63f80e9ff83e6c693d4d562473d1aa0e0";
        };
        nativeBuildInputs = [ pkgs.autoPatchelfHook ];
        buildInputs = [ pkgs.stdenv.cc.cc.lib pkgs.expat pkgs.zlib ];
        doCheck = false;
      };
      ll311 = pkgs.python311.pkgs.librelane.override {
        ciel = ciel311;
        klayout = klayout311;
        yosys = pkgs.yosys // {
          withPythonPackages = embeddedPython pkgs.yosys;
        };
        openroad = pkgs.openroad // {
          withPythonPackages = embeddedPython pkgs.openroad;
        };
      };
      python = pkgs.python311.withPackages (ps: [ ll311 ps.pip ]);
    in {
      default = pkgs.buildEnv {
        name = "ttsky-librelane-3.0.14-python311";
        paths = [ python pkgs.git pkgs.iverilog pkgs.cairo pkgs.zlib pkgs.expat pkgs.stdenv.cc.cc.lib ] ++ ll311.includedTools;
        ignoreCollisions = true;
      };
    });
  };
}
