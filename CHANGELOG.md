# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- IIC-OSIC-style X11, VNC, shell and Jupyter launch commands, shared runtime configuration and compatible `/foss` paths.
- `sak-pdk` compatibility alongside `set_pdk`, project `.designinit` support and explicit GF180MCU D selection.
- Host runtime contracts and GF180MCU analog, KLayout and LibreLane integration coverage.
### Fixed
- Command argument preservation and GUI process supervision at container startup.
- GF180MCU resource preservation and deterministic PDK patching.
- Release tests retain failure artifacts before cleanup and publication remains gated on tests.
### Removed
- Superseded shell configurations, unused installation helpers and obsolete GF comparison scripts; selected tool revisions are unchanged.

## [0.1.0] - 2025-05-05
### Added
- Initial public release of UNIC-CASS IC Design Tools.
- Docker environment with open-source EDA tools and PDKs (sky130A, gf180mcuD, ihp-sg13g2).
- Documentation, usage instructions, and community guidelines. 