FROM docker.io/library/node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    HOME=/antigravity-home \
    EDITOR=nano \
    VISUAL=nano \
    AGY_CLI_DISABLE_AUTO_UPDATE=true

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        bash bubblewrap bzip2 ca-certificates coreutils curl dbus diffutils \
        file findutils gawk git gnome-keyring grep gzip jq less libc6 \
        libgcc-s1 libsecret-1-0 libsecret-tools libstdc++6 nano patch podman \
        procps python3 ripgrep sed tar unzip util-linux xz-utils zip \
    && npm install --global --omit=dev @fission-ai/openspec \
    && printf '\nunset historylog\n' >> /etc/nanorc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm \
    && mkdir -p /antigravity-home \
    && chmod 1777 /antigravity-home

# The official installer selects the architecture and verifies the manifest's
# SHA-512 checksum. Explicit wrapper rebuilds disable the build cache.
RUN curl --fail --show-error --silent --location \
        https://antigravity.google/cli/install.sh -o /tmp/agy-install.sh \
    && HOME=/root bash /tmp/agy-install.sh --dir /usr/local/bin \
    && rm -rf /tmp/agy-install.sh /root/.cache/antigravity /root/.local \
    && agy --version \
    && file /usr/local/bin/agy \
    && openspec --version

COPY container-entrypoint.sh /usr/local/bin/antigravity-entrypoint
COPY keyring-session.sh /usr/local/lib/antigravity/keyring-session.sh
RUN chmod 755 /usr/local/bin/antigravity-entrypoint /usr/local/lib/antigravity/keyring-session.sh

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/antigravity-entrypoint"]
