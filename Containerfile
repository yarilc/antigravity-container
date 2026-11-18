# Image inputs are pinned. Update them only through the maintenance procedure in
# README.md ("Updating pinned image inputs") and record the result in docs/validation.md.
FROM docker.io/library/node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da

ARG OPENSPEC_VERSION=2.0.0
# Official agy release artifacts and SHA-512 values, as listed on 2026-11-09 by
# https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_<arch>.json
ARG AGY_VERSION=1.5.3
ARG AGY_URL_AMD64=https://storage.googleapis.com/antigravity-public/antigravity-cli/1.5.3-6604829099950080/linux-x64/cli_linux_x64.tar.gz
ARG AGY_SHA512_AMD64=e363e1b17daaac2589f18e6973429c039fd5a5e5c15e9c0852fa349836f3992b10fe84732bc8d8c8208e149f0304f15aba9dec696d12efeed03917492c0580eb
ARG AGY_URL_ARM64=https://storage.googleapis.com/antigravity-public/antigravity-cli/1.5.3-6604829099950080/linux-arm/cli_linux_arm64.tar.gz
ARG AGY_SHA512_ARM64=c2fac818b3c1bb224079df03a714ccba99728b6a3a41d86d247ab2feb8582a43840c5032f1c2b75e72667623d5503e7ffda2712c4f37b6ee19f99c3fcfb25bae

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/antigravity-home \
    EDITOR=nano \
    VISUAL=nano \
    AGY_CLI_DISABLE_AUTO_UPDATE=true

# Debian packages are fetched only over verified HTTPS, so builds need no outbound
# port 80. The slim base has no ca-certificates, so the pinned base's Node.js root
# certificates verify the fetches until Debian ca-certificates is installed. With
# host CA trust enabled, the selected bundle arrives as the optional build-ca
# secret (never stored in a layer) and is appended for TLS-intercepting networks.
# The temporary bundle stays readable by apt's _apt user and is removed in this step.
RUN --mount=type=secret,id=build-ca,required=false \
    node -e 'process.stdout.write(require("tls").rootCertificates.join("\n") + "\n")' \
        > /tmp/apt-bootstrap-ca.pem \
    && if [ -s /run/secrets/build-ca ]; then cat /run/secrets/build-ca >> /tmp/apt-bootstrap-ca.pem; fi \
    && sed -i 's|^URIs: http://|URIs: https://|' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::https::CAInfo=/tmp/apt-bootstrap-ca.pem update \
    && apt-get -o Acquire::https::CAInfo=/tmp/apt-bootstrap-ca.pem install --no-install-recommends -y \
        bash bubblewrap bzip2 ca-certificates coreutils curl diffutils \
        file findutils gawk git grep gzip jq less libc6 \
        libgcc-s1 libstdc++6 nano openssl patch podman \
        procps python3 ripgrep sed tar unzip util-linux xz-utils zip \
    && rm -f /tmp/apt-bootstrap-ca.pem \
    && npm install --global --omit=dev "@fission-ai/openspec@${OPENSPEC_VERSION}" \
    && printf '\nunset historylog\n' >> /etc/nanorc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm \
    && mkdir -p /antigravity-home /workspace \
    && chmod 1777 /antigravity-home

# Install the recorded official artifact for this architecture after verifying
# its SHA-512. Explicit wrapper rebuilds disable the build cache. The download
# verifies TLS against the image roots plus the optional build-ca secret (host CA
# trust); the combined bundle lives in /tmp/agy and is removed with it.
RUN --mount=type=secret,id=build-ca,required=false \
    case "$(uname -m)" in \
        x86_64|amd64) agy_url="$AGY_URL_AMD64"; agy_sha512="$AGY_SHA512_AMD64" ;; \
        aarch64|arm64) agy_url="$AGY_URL_ARM64"; agy_sha512="$AGY_SHA512_ARM64" ;; \
        *) echo "Unsupported architecture for agy: $(uname -m)" >&2; exit 1 ;; \
    esac \
    && mkdir /tmp/agy \
    && cat /etc/ssl/certs/ca-certificates.crt > /tmp/agy/ca.pem \
    && if [ -s /run/secrets/build-ca ]; then cat /run/secrets/build-ca >> /tmp/agy/ca.pem; fi \
    && curl --fail --show-error --silent --location --cacert /tmp/agy/ca.pem "$agy_url" -o /tmp/agy/agy.tar.gz \
    && printf '%s  /tmp/agy/agy.tar.gz\n' "$agy_sha512" | sha512sum --check --strict - \
    && tar -xzf /tmp/agy/agy.tar.gz -C /tmp/agy antigravity \
    && install -m 0755 /tmp/agy/antigravity /usr/local/bin/agy \
    && rm -rf /tmp/agy \
    && agy_reported=$(agy --version) \
    && case "$agy_reported" in "$AGY_VERSION"|"$AGY_VERSION "*) ;; *) echo "agy reports $agy_reported, expected $AGY_VERSION" >&2; exit 1 ;; esac \
    && file /usr/local/bin/agy \
    && openspec --version

COPY container-entrypoint.sh /usr/local/bin/antigravity-entrypoint
# The loopback relay and its multiplex module run inside restricted sessions; the
# guard itself is never part of the image.
COPY network/relay.py network/mux.py /opt/sandbox-egress/
RUN chmod 755 /usr/local/bin/antigravity-entrypoint \
    && chmod 644 /opt/sandbox-egress/relay.py /opt/sandbox-egress/mux.py

# /workspace is created in the package step above: a WORKDIR missing from every
# layer is created and chowned by the engine at each container start, which
# fails for large domain UIDs under --userns=keep-id.
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/antigravity-entrypoint"]
