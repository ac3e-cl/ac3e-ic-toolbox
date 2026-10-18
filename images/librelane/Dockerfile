# Focused installer validation on an existing toolbox image, not a source rebuild.
ARG TOOLBOX_IMAGE=isaiash/ac3e-ic-toolbox:0.1.0
FROM ${TOOLBOX_IMAGE}
USER root
RUN mkdir -p /opt/librelane-templates && chown designer:designer /opt/librelane-templates
COPY --chmod=755 images/librelane/librelane-template /usr/local/bin/librelane-template
USER designer
ARG MAX_BUILD_JOBS=2
RUN --mount=type=bind,source=images/librelane,target=/images/librelane \
    --mount=type=bind,source=manifest.json,target=/images/manifest.json \
    bash /images/librelane/install.sh /images/manifest.json
