# Based on https://github.com/iic-jku/IIC-OSIC-TOOLS/blob/main/_build/Dockerfile

# Default required for `docker build --check`; manifest.json overrides at build time.
ARG BASE_IMAGE=ubuntu:22.04

# ngspice
ARG NGSPICE_REPO_URL
ARG NGSPICE_REPO_COMMIT
ARG NGSPICE_NAME

# GNUCAP: 20260729-dev
ARG GNUCAP_REPO_URL
ARG GNUCAP_REPO_COMMIT
ARG GNUCAP_NAME

# Xyce
ARG XYCE_REPO_URL
ARG XYCE_REPO_COMMIT
ARG XYCE_TRILINOS_REPO_URL
ARG XYCE_TRILINOS_REPO_COMMIT
ARG XYCE_NAME

# Open PDKs
ARG OPEN_PDKS_REPO_URL
ARG OPEN_PDKS_REPO_COMMIT
ARG OPEN_PDKS_NAME

# Magic
ARG MAGIC_REPO_URL
ARG MAGIC_REPO_COMMIT
ARG MAGIC_NAME

# IHP Open PDK
ARG IHP_PDK_REPO_URL
ARG IHP_PDK_REPO_COMMIT
ARG IHP_PDK_REPO_BRANCH
ARG IHP_PDK_NAME

# OpenVAF
ARG OPENVAF_REPO_URL
ARG OPENVAF_REPO_COMMIT
ARG OPENVAF_DOWNLOAD
ARG OPENVAF_NAME

# KLayout
ARG KLAYOUT_REPO_URL
ARG KLAYOUT_REPO_COMMIT
ARG KLAYOUT_DOWNLOAD
ARG KLAYOUT_NAME

# xschem
ARG XSCHEM_REPO_URL
ARG XSCHEM_REPO_COMMIT
ARG XSCHEM_NAME

# Netgen
ARG NETGEN_REPO_URL
ARG NETGEN_REPO_COMMIT
ARG NETGEN_NAME

# gaw3 for xschem
ARG GAW3_XSCHEM_REPO_URL
ARG GAW3_XSCHEM_REPO_COMMIT
ARG GAW3_XSCHEM_NAME

# Yosys
ARG YOSYS_REPO_URL
ARG YOSYS_REPO_COMMIT
ARG YOSYS_NAME
ARG YOSYS_EQY_REPO_URL
ARG YOSYS_EQY_NAME
ARG YOSYS_SBY_REPO_URL
ARG YOSYS_SBY_NAME
ARG YOSYS_MCY_REPO_URL
ARG YOSYS_MCY_NAME

# CVC-RV
ARG CVC_RV_REPO_URL
ARG CVC_RV_REPO_COMMIT
ARG CVC_RV_NAME

# Verilator
ARG VERILATOR_REPO_URL
ARG VERILATOR_REPO_COMMIT
ARG VERILATOR_NAME

# Icarus Verilog
ARG IVERILOG_REPO_URL
ARG IVERILOG_REPO_COMMIT
ARG IVERILOG_NAME

# GTKWave
ARG GTKWAVE_REPO_URL
ARG GTKWAVE_REPO_COMMIT
ARG GTKWAVE_NAME

# OpenROAD
ARG OPENROAD_REPO_URL
ARG OPENROAD_REPO_COMMIT
ARG OPENROAD_NAME

# OpenROAD-flow-scripts
ARG ORFS_REPO_URL
ARG ORFS_REPO_COMMIT
ARG ORFS_NAME

ARG NIX_INSTALLER_URL
ARG NIX_SUBSTITUTER_URL
ARG NIX_SUBSTITUTER_PUBLIC_KEY
ARG LIBRELANE_REPO_URL
ARG LIBRELANE_REPO_COMMIT
ARG ENABLE_GUI
ARG MAX_BUILD_JOBS
ARG PYTHON_VERSION
ARG PYTHON_SOURCE_SHA256

#######################################################################
# Basic configuration for base and builder
#######################################################################

FROM ${BASE_IMAGE} AS common
# Limit build parallelism to reduce RAM usage (default: 2 for memory-constrained builds)
ARG MAX_BUILD_JOBS
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Europe/Vienna \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    TOOLS=/opt \
    PDK_ROOT=/opt/pdks \
    MAX_BUILD_JOBS=${MAX_BUILD_JOBS}

USER root


#######################################################################
# Side-by-side user Python; Ubuntu's /usr/bin/python3 remains unchanged.
#######################################################################
FROM common AS python_builder
ARG PYTHON_VERSION \
    PYTHON_SOURCE_SHA256
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xz-utils build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev libffi-dev liblzma-dev \
    libgdbm-dev libgdbm-compat-dev libncursesw5-dev uuid-dev tk-dev && \
    rm -rf /var/lib/apt/lists/*
RUN --mount=type=bind,source=images/python,target=/images/python \
    bash /images/python/install.sh

#######################################################################
# Setup base image
#######################################################################
FROM common AS base

ARG ENABLE_GUI
ENV ENABLE_GUI=${ENABLE_GUI}

# From build/images/base/Dockerfile IIC_OSIC_TOOLS
ENV VNC_PORT=5901 \
    NO_VNC_PORT=80
EXPOSE $VNC_PORT $NO_VNC_PORT 

# Environment config
ENV NO_VNC_HOME=/usr/share/novnc \
    VNC_COL_DEPTH=24 \
    VNC_RESOLUTION=1680x1050 \
    VNC_PW=abc123 \
    VNC_VIEW_ONLY=false

RUN --mount=type=bind,source=images/base,target=/images/base \
    bash /images/base/base_install.sh
COPY --from=python_builder /opt/python /opt/python
ENV EDA_VENV=/opt/eda-venv
ENV PATH="${EDA_VENV}/bin:$PATH"
RUN --mount=type=bind,source=images/base,target=/images/base \
    bash /images/base/python_packages.sh


#######################################################################
# Shared native builder: no LLVM, Qt, MPI or OpenROAD source dependencies.
#######################################################################
FROM common AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    locales ca-certificates build-essential autoconf automake autotools-dev \
    libtool pkg-config bison flex gawk git curl wget unzip zip patch autopoint gperf \
    cmake ninja-build python3 python3-dev python3-pip python3-numpy \
    tcl tcl-dev tk-dev libreadline-dev libffi-dev libpcre2-dev \
    libx11-dev libxaw7-dev libxpm-dev libxrender-dev libxft-dev libglu1-mesa-dev \
    libcairo2-dev libgtk-3-dev libgtk2.0-dev libfftw3-dev \
    libsuitesparse-dev libedit-dev libfl-dev zlib1g-dev libbz2-dev \
    liblzma-dev libgmp-dev libssl-dev gettext help2man texinfo time bc csh && \
    sed -i -e "s/# $LC_ALL UTF-8/$LC_ALL UTF-8/" /etc/locale.gen && \
    locale-gen && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 0 && \
    rm -rf /var/lib/apt/lists/*

# Preserve the exhaustive system toolchain only for LLVM/Trilinos/OpenROAD.
# The existing installer supplies their compiler and system-library requirements;
# ordinary native tools must not wait for it or the source dependency builds.
FROM builder AS heavyweight_builder
RUN --mount=type=bind,source=images/builder,target=/images/builder \
    bash /images/builder/exhaustive-install.sh

FROM heavyweight_builder AS openroad_dependencies
# Initialize CMAKE_PACKAGE_ROOT_ARGS variable
ENV CMAKE_PACKAGE_ROOT_ARGS=""
ENV CMAKE_PACKAGE_ROOT_ARGS="$CMAKE_PACKAGE_ROOT_ARGS -D SWIG_ROOT=$TOOLS/common -D Eigen3_ROOT=$TOOLS/common -D GTest_ROOT=$TOOLS/common -D LEMON_ROOT=$TOOLS/common -D spdlog_ROOT=$TOOLS/common -D ortools_ROOT=$TOOLS/common"

RUN --mount=type=bind,source=images/boost,target=/images/boost \
    bash /images/boost/install.sh
RUN --mount=type=bind,source=images/swig,target=/images/swig \
    bash /images/swig/install.sh
RUN --mount=type=bind,source=images/eigen,target=/images/eigen \
    bash /images/eigen/install.sh
RUN --mount=type=bind,source=images/cudd,target=/images/cudd \
    bash /images/cudd/install.sh
RUN --mount=type=bind,source=images/cusp,target=/images/cusp \
    bash /images/cusp/install.sh
RUN --mount=type=bind,source=images/lemon,target=/images/lemon \
    bash /images/lemon/install.sh
RUN --mount=type=bind,source=images/spdlog,target=/images/spdlog \
    bash /images/spdlog/install.sh
RUN --mount=type=bind,source=images/gtest,target=/images/gtest \
    bash /images/gtest/install.sh
RUN --mount=type=bind,source=images/ortools,target=/images/ortools \
    bash /images/ortools/install.sh

ENV PATH="$TOOLS/common/bin:$PATH"
ENV LD_LIBRARY_PATH="$TOOLS/common/lib64:$TOOLS/common/lib"

# Cleanup: Remove temporary files and build artifacts from builder stage
# Note: Don't delete .a files from /usr as they might be needed for linking
RUN rm -rf /tmp/* /var/tmp/* && \
    find /usr -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true


#######################################################################
# Compile magic (also required to build the GF180 PDK)
#######################################################################
FROM builder AS magic

ARG MAGIC_REPO_URL \
    MAGIC_REPO_COMMIT \
    MAGIC_NAME

RUN --mount=type=bind,source=images/magic,target=/images/magic \
    bash /images/magic/install.sh


#######################################################################
# Build PDKs from open_pdks
#######################################################################
FROM magic AS pdk_builder

ARG OPEN_PDKS_REPO_URL \
    OPEN_PDKS_REPO_COMMIT \
    OPEN_PDKS_NAME

RUN pip install --no-cache-dir volare==0.18.1

FROM pdk_builder AS gf180_pdk
RUN --mount=type=bind,source=images/pdks,target=/images/pdks \
    cd /images/pdks/ \
    && bash install_gf180mcu.sh
RUN --mount=type=bind,source=images/final_structure/configure,target=/images/final_structure/configure \
    cd /images/final_structure/configure/ \
    && bash patch_pdk_gf180mcu.sh

# Compatibility target. Copy whole roots, preserving Volare backing directories
# and the relative public symlinks (in particular GF180 D's private A backing).
FROM pdk_builder AS open_pdks
COPY --from=gf180_pdk ${PDK_ROOT} ${PDK_ROOT}

#######################################################################
# Compile openvaf (requirement for ihp pdk)
#######################################################################
FROM heavyweight_builder AS openvaf

ARG OPENVAF_REPO_URL \
    OPENVAF_REPO_COMMIT \
    OPENVAF_DOWNLOAD \
    OPENVAF_NAME
ENV OPENVAF_NAME=${OPENVAF_NAME}

RUN --mount=type=bind,source=images/openvaf,target=/images/openvaf \
    bash /images/openvaf/install.sh


#######################################################################
# Build ihp pdk open pdk
#######################################################################
FROM openvaf AS ihp_pdk

ARG IHP_PDK_REPO_URL \
    IHP_PDK_REPO_COMMIT \
    IHP_PDK_REPO_BRANCH \
    IHP_PDK_NAME

RUN --mount=type=bind,source=images/ihp_pdk,target=/images/ihp_pdk \
    bash /images/ihp_pdk/install.sh


#######################################################################
# Compile ngspice
#######################################################################
FROM builder AS ngspice

ARG NGSPICE_REPO_URL \
    NGSPICE_REPO_COMMIT \
    NGSPICE_NAME

RUN --mount=type=bind,source=images/ngspice,target=/images/ngspice \
    bash /images/ngspice/install.sh

#######################################################################
# Compile GNUCAP (official standalone build, no heavyweight builder dependencies)
#######################################################################
FROM common AS gnucap
ARG GNUCAP_REPO_URL \
    GNUCAP_REPO_COMMIT \
    GNUCAP_NAME
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git build-essential libreadline-dev && \
    rm -rf /var/lib/apt/lists/*
RUN --mount=type=bind,source=images/gnucap,target=/images/gnucap \
    bash /images/gnucap/install.sh

#######################################################################
# Compile xyce
#######################################################################
FROM heavyweight_builder AS xyce

ARG XYCE_REPO_URL \
    XYCE_REPO_COMMIT \
    XYCE_NAME \
    XYCE_TRILINOS_REPO_URL \
    XYCE_TRILINOS_REPO_COMMIT

RUN --mount=type=bind,source=images/xyce,target=/images/xyce \
    bash /images/xyce/install.sh
    
#######################################################################
# Compile xschem
#######################################################################
FROM builder AS xschem

ARG XSCHEM_REPO_URL \
    XSCHEM_REPO_COMMIT \
    XSCHEM_NAME

RUN --mount=type=bind,source=images/xschem,target=/images/xschem \
    bash /images/xschem/install.sh


#######################################################################
# Compile yosys
#######################################################################
FROM builder AS yosys

ARG YOSYS_REPO_URL \
    YOSYS_REPO_COMMIT \
    YOSYS_NAME \
    YOSYS_EQY_REPO_URL \
    YOSYS_EQY_NAME \
    YOSYS_SBY_REPO_URL \
    YOSYS_SBY_NAME \
    YOSYS_MCY_REPO_URL \
    YOSYS_MCY_NAME

RUN --mount=type=bind,source=images/yosys,target=/images/yosys \
    bash /images/yosys/install.sh

#######################################################################
# Compile netgen
#######################################################################
FROM builder AS netgen

ARG NETGEN_REPO_URL \
    NETGEN_REPO_COMMIT \
    NETGEN_NAME

RUN --mount=type=bind,source=images/netgen,target=/images/netgen \
    bash /images/netgen/install.sh


#######################################################################
# Compile gaw
#######################################################################
FROM builder AS gaw

ARG GAW3_XSCHEM_REPO_URL \
    GAW3_XSCHEM_REPO_COMMIT \
    GAW3_XSCHEM_NAME

RUN --mount=type=bind,source=images/gaw,target=/images/gaw \
    bash /images/gaw/install.sh


#######################################################################
# Compile gtkwave
#######################################################################
# FROM builder AS gtkwave
# ARG GTKWAVE_REPO_URL \
#     GTKWAVE_REPO_COMMIT \
#     GTKWAVE_NAME

# RUN --mount=type=bind,source=images/gtkwave,target=/images/gtkwave \
#     bash /images/gtkwave/install.sh


#######################################################################
# Compile cvc_rv
#######################################################################
FROM builder AS cvc_rv

ARG CVC_RV_REPO_URL \
    CVC_RV_REPO_COMMIT \
    CVC_RV_NAME

RUN --mount=type=bind,source=images/cvc_rv,target=/images/cvc_rv \
    bash /images/cvc_rv/install.sh


#######################################################################
# Compile verilator
#######################################################################
FROM builder AS verilator

ARG VERILATOR_REPO_URL \
    VERILATOR_REPO_COMMIT \
    VERILATOR_NAME

RUN --mount=type=bind,source=images/verilator,target=/images/verilator \
    bash /images/verilator/install.sh

    
#######################################################################
# Compile iverilog
#######################################################################
FROM builder AS iverilog

ARG IVERILOG_REPO_URL \
    IVERILOG_REPO_COMMIT \
    IVERILOG_NAME

RUN --mount=type=bind,source=images/iverilog,target=/images/iverilog \
    bash /images/iverilog/install.sh


#######################################################################
# Compile OpenROAD (core application)
#######################################################################
FROM openroad_dependencies AS openroad_core

ARG OPENROAD_REPO_URL \
    OPENROAD_REPO_COMMIT \
    OPENROAD_NAME

RUN --mount=type=bind,source=images/openroad,target=/images/openroad \
    bash /images/openroad/install.sh

#######################################################################
# Clone OpenROAD-flow-scripts (ORFS)
#######################################################################
FROM base AS orfs

ARG ORFS_REPO_URL \
    ORFS_REPO_COMMIT \
    ORFS_NAME

RUN --mount=type=bind,source=images/orfs,target=/images/orfs \
    bash /images/orfs/install.sh


#######################################################################
# Shared runtime for the standard image
#######################################################################
FROM base AS ac3e-ic-toolbox-base
ARG NGSPICE_REPO_COMMIT \
    OPEN_PDKS_REPO_COMMIT \
    MAGIC_REPO_COMMIT \
    IHP_PDK_REPO_COMMIT \
    IHP_PDK_NAME \
    KLAYOUT_DOWNLOAD \
    XSCHEM_REPO_COMMIT \
    NETGEN_REPO_COMMIT


RUN --mount=type=bind,source=images/final_structure/install,target=/images/final_structure/install \
    bash /images/final_structure/install/install_klayout.sh

# Install libyaml-cpp for OpenROAD (combined with cleanup)
RUN apt-get update && \
    apt-get install -y libyaml-cpp-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /var/tmp/*

RUN --mount=type=bind,source=images/final_structure/configure,target=/images/final_structure/configure \
    cd /images/final_structure/configure/ \
    && bash tool_configuration.sh

COPY --from=open_pdks  ${PDK_ROOT}                  ${PDK_ROOT}
COPY --from=ihp_pdk    ${PDK_ROOT}/${IHP_PDK_NAME}  ${PDK_ROOT}/${IHP_PDK_NAME}
COPY --from=ihp_pdk    ${PDK_ROOT}/versions.txt     ${PDK_ROOT}/versions.txt

# Retain common shared libraries used by OpenROAD, not just its executable.
COPY --from=openroad_dependencies ${TOOLS}/common   ${TOOLS}/common

# Cleanup compile-time only tools from common (SWIG, GTest are only needed at build time)
RUN rm -rf ${TOOLS}/common/bin/swig* ${TOOLS}/common/share/swig && \
    find ${TOOLS}/common -name "*gtest*" -type f -delete && \
    find ${TOOLS}/common -name "*GTest*" -type f -delete && \
    find ${TOOLS}/common -type d -name "*gtest*" -exec rm -rf {} + 2>/dev/null || true
COPY --from=ihp_pdk    ${TOOLS}/openvaf             ${TOOLS}/openvaf
COPY --from=ngspice    ${TOOLS}/ngspice             ${TOOLS}/ngspice
COPY --from=gnucap     ${TOOLS}/gnucap              ${TOOLS}/gnucap
COPY --from=xschem     ${TOOLS}/xschem               ${TOOLS}/xschem
COPY --from=magic      ${TOOLS}/magic               ${TOOLS}/magic
COPY --from=netgen     ${TOOLS}/netgen              ${TOOLS}/netgen
COPY --from=gaw        ${TOOLS}/gaw3-xschem         ${TOOLS}/gaw3-xschem
COPY --from=cvc_rv     ${TOOLS}/cvc_rv              ${TOOLS}/cvc_rv
COPY --from=verilator  ${TOOLS}/verilator           ${TOOLS}/verilator
COPY --from=iverilog   ${TOOLS}/iverilog            ${TOOLS}/iverilog
COPY --from=yosys      ${TOOLS}/yosys               ${TOOLS}/yosys
COPY --from=openroad_core ${TOOLS}/openroad         ${TOOLS}/openroad
COPY --from=orfs       ${TOOLS}/OpenROAD-flow-scripts ${TOOLS}/OpenROAD-flow-scripts

# Strip binaries to reduce image size (20-30% reduction on executables)
RUN find /opt -type f -executable -not -path "*/common/*" -exec file {} \; | \
    grep -E "(ELF.*executable|shared object)" | \
    cut -d: -f1 | \
    xargs -r strip --strip-unneeded 2>/dev/null || true

# Ensure OpenROAD and OpenVAF are in PATH for all users
ENV PATH="$TOOLS/openroad/bin:$TOOLS/openvaf/bin:$PATH"

RUN --mount=type=bind,source=images/final_structure/configure,target=/images/final_structure/configure \
    cd /images/final_structure/configure/ \
    && bash modify_user.sh

# Create /run/user/1000/ directory for X11 and systemd runtime files
RUN mkdir -p /run/user/1000 && \
    chmod 700 /run/user/1000 && \
    chown designer:designer /run/user/1000

# Fix IHP permissions (after designer user is created)
RUN chown -R designer:designer /opt/pdks/ihp-sg13g2/

# One runtime configuration for interactive, login and batch shells.
COPY images/final_structure/configure/pdk.sh /opt/ac3e-ic-toolbox/config/
COPY images/final_structure/configure/ac3e-ic-toolbox-env.sh /opt/ac3e-ic-toolbox/config/
COPY images/final_structure/configure/profile.sh /opt/ac3e-ic-toolbox/config/
COPY images/final_structure/configure/profile.sh /etc/profile.d/ac3e-ic-toolbox.sh
COPY images/final_structure/configure/.bashrc /home/designer/.bashrc
COPY images/final_structure/configure/.bashrc /root/.bashrc
RUN mkdir -p /foss && \
    ln -s /opt /foss/tools && \
    ln -s /opt/pdks /foss/pdks && \
    ln -s /home/designer/shared /foss/designs && \
    ln -s /home/designer /headless && \
    mkdir -p /home/designer/shared /home/designer/.klayout && \
    chown designer:designer /home/designer/shared /home/designer/.klayout /home/designer/.bashrc
ENV DESIGNS=/foss/designs

# Bundled stdio MCP, isolated from the EDA Python environment.
RUN --mount=type=bind,source=images/mcp,target=/images/mcp \
    bash /images/mcp/install.sh

# Patch IHP PDK for KLayout DRC compatibility
RUN --mount=type=bind,source=images/final_structure/configure,target=/images/final_structure/configure \
    cd /images/final_structure/configure/ \
    && bash patch_pdk_ihp.sh

# Run xschem install.py script as designer user
USER designer
RUN cd /opt/pdks/ihp-sg13g2/libs.tech/xschem && \
    PATH="$TOOLS/openvaf/bin:$PATH" USER=designer python install.py

COPY --chmod=755 images/final_structure/configure/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

WORKDIR /home/designer
USER designer

ENV NGSPICE_REPO_COMMIT=${NGSPICE_REPO_COMMIT} \
    OPEN_PDKS_REPO_COMMIT=${OPEN_PDKS_REPO_COMMIT} \
    MAGIC_REPO_COMMIT=${MAGIC_REPO_COMMIT} \
    IHP_PDK_REPO_COMMIT=${IHP_PDK_REPO_COMMIT} \
    KLAYOUT_DOWNLOAD=${KLAYOUT_DOWNLOAD} \
    XSCHEM_REPO_COMMIT=${XSCHEM_REPO_COMMIT} \
    NETGEN_REPO_COMMIT=${NETGEN_REPO_COMMIT}

#######################################################################
# Standard output image, including Nix package manager and LibreLane
#######################################################################
FROM ac3e-ic-toolbox-base AS ac3e-ic-toolbox
ARG NIX_INSTALLER_URL \
    NIX_SUBSTITUTER_URL \
    NIX_SUBSTITUTER_PUBLIC_KEY \
    LIBRELANE_REPO_URL \
    LIBRELANE_REPO_COMMIT
USER root

# Install sudo for Nix installer
RUN apt-get update && apt-get install -y sudo && rm -rf /var/lib/apt/lists/*

# Switch to designer user to install Nix in single-user mode
USER designer

# Install Nix in single-user mode for designer user
RUN curl -L "$NIX_INSTALLER_URL" | sh -s -- --no-daemon --yes

# Configure Nix with custom substituters and enable flakes
RUN mkdir -p ~/.config/nix && \
    echo "extra-substituters = $NIX_SUBSTITUTER_URL" > ~/.config/nix/nix.conf && \
    echo "extra-trusted-public-keys = $NIX_SUBSTITUTER_PUBLIC_KEY" >> ~/.config/nix/nix.conf && \
    echo 'experimental-features = nix-command flakes' >> ~/.config/nix/nix.conf

# Add USER variable to .profile (required by nix.sh)
RUN sed -i '/if \[ -e \/home\/designer\/.nix-profile/i export USER=designer' ~/.profile

# Clone LibreLane repository
USER root
RUN git clone "$LIBRELANE_REPO_URL" /opt/librelane && \
    git -C /opt/librelane checkout --detach "$LIBRELANE_REPO_COMMIT" && \
    chown -R designer:designer /opt/librelane

# Create /opt/pdks/ciel with proper permissions for LibreLane
RUN mkdir -p /opt/pdks/ciel && chown -R designer:designer /opt/pdks/ciel

USER designer
ENV HOME=/home/designer USER=designer
SHELL ["/bin/bash", "-c"]

# Install the manifest-pinned LibreLane revision using Nix
RUN cd /opt/librelane && \
    source ~/.nix-profile/etc/profile.d/nix.sh && \
    nix profile install . --extra-experimental-features "nix-command flakes"

# Verify LibreLane installation
RUN source ~/.nix-profile/etc/profile.d/nix.sh && \
    librelane --version

# Preserve each upstream template's Nix lock and PDK independently of /opt/pdks.
USER root
RUN mkdir -p /opt/librelane-templates && chown designer:designer /opt/librelane-templates
COPY --chmod=755 images/librelane/librelane-template /usr/local/bin/librelane-template
USER designer
ARG MAX_BUILD_JOBS
RUN --mount=type=bind,source=images/librelane,target=/images/librelane \
    --mount=type=bind,source=manifest.json,target=/images/manifest.json \
    bash /images/librelane/install.sh /images/manifest.json

# Note: yosys is already installed via the yosys stage, skip Nix installation to avoid rate limits
# RUN source ~/.nix-profile/etc/profile.d/nix.sh && \
#     nix profile install nixpkgs#yosys --extra-experimental-features "nix-command flakes"

# Configure /etc/bash.bashrc for interactive shells and replace .bashrc with Nix-compatible version
USER root
RUN --mount=type=bind,source=images/final_structure/configure,target=/images/final_structure/configure \
    sed 's/\r$//' /images/final_structure/configure/etc_bash.bashrc_nix > /etc/bash.bashrc && \
    sed 's/\r$//' /images/final_structure/configure/.bashrc > /home/designer/.bashrc && \
    chown designer:designer /home/designer/.bashrc && \
    chmod o+x /home/designer

USER designer
