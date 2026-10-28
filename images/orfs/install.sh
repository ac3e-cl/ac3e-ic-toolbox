#!/bin/bash
set -euo pipefail

: "${TOOLS:?}" "${ORFS_NAME:?}" "${ORFS_REPO_URL:?}" "${ORFS_REPO_COMMIT:?}"

# Runtime resources only. OpenROAD, Yosys and yosys-slang are built separately;
# the three source gitlinks in the pinned ORFS revision must never be fetched.
# Explicitly disable recursion even when a builder's Git config enables it.
git -c submodule.recurse=false clone --no-recurse-submodules --depth 1 \
    "$ORFS_REPO_URL" "$TOOLS/$ORFS_NAME"
cd "$TOOLS/$ORFS_NAME"
git -c submodule.recurse=false fetch --no-recurse-submodules --depth 1 origin "$ORFS_REPO_COMMIT"
git -c submodule.recurse=false checkout --detach "$ORFS_REPO_COMMIT"

# The pinned flow/Makefile includes settings.mk before scripts/variables.mk.
# Its non-Nix defaults otherwise point at tools/install binaries which this
# distribution deliberately does not build. Resolve separately installed tools
# at runtime; environment and command-line overrides retain their precedence.
printf '%s\n' \
    '# Runtime-only distribution: use independently installed executables.' \
    'export OPENROAD_EXE ?= $(shell command -v openroad)' \
    'export OPENSTA_EXE ?= $(shell command -v sta)' \
    'export YOSYS_EXE ?= $(shell command -v yosys)' > flow/settings.mk

# Keep immutable provenance before deleting Git's object database. Gitlinks are
# recorded, not initialized; their SHAs identify sources absent from this image.
git rev-parse HEAD > ORFS_REVISION
{
    printf 'repository=%s\ncommit=%s\n' "$ORFS_REPO_URL" "$(cat ORFS_REVISION)"
    git ls-tree -r HEAD | while IFS=$'\t' read -r entry path; do
        if [[ "$entry" == '160000 commit '* ]]; then
            printf '%s\t%s\n' "${entry#160000 commit }" "$path"
        fi
    done
} > ORFS_PROVENANCE
rm -rf .git
