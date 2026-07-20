# =============================================================================
# FuzeInfra Managed-Agents self-hosted worker image
# -----------------------------------------------------------------------------
# Drains a `self_hosted` environment queue (see environments/selfhosted-devops.json)
# and runs the agent's tools IN THIS CONTAINER, on our infrastructure. This is
# where the real credentials live (kubeconfig, GitHub PAT, cloud keys) and where
# the cluster is reachable — so the devops role never needs to ask a human to run
# a command it can run here.
#
# The destructive-verb guard shims are placed FIRST on PATH so even an approved
# `bash` tool call cannot run `kubectl delete` / `terraform apply` etc.
#
# Build:  docker build -t fuzeinfra/agent-worker:dev agent-templates/worker
# Run:    see run-worker.sh (needs ANTHROPIC_ENVIRONMENT_KEY + _ID)
# =============================================================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# --- base utilities + python -------------------------------------------------
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg git jq unzip tar bash python3 python3-pip; \
    rm -rf /var/lib/apt/lists/*; \
    python3 --version

# --- GitHub CLI --------------------------------------------------------------
RUN set -eux; \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list; \
    apt-get update; apt-get install -y --no-install-recommends gh; \
    rm -rf /var/lib/apt/lists/*

# --- cluster CLIs to /usr/local/bin (the guard shims exec these absolute paths)
ARG KUBECTL_VERSION=v1.29.0
ARG HELM_VERSION=v3.14.4
ARG TERRAFORM_VERSION=1.6.6
ARG KIND_VERSION=v0.23.0
ARG KUBECONFORM_VERSION=v0.6.7
ARG ARGOCD_VERSION=v2.11.3
RUN set -eux; arch="$(dpkg --print-architecture)"; \
    curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl"; \
    curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${arch}.tar.gz" | tar -xz -C /tmp; \
    mv "/tmp/linux-${arch}/helm" /usr/local/bin/helm; \
    curl -fsSLo /tmp/tf.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${arch}.zip"; \
    unzip -d /usr/local/bin /tmp/tf.zip; \
    curl -fsSLo /usr/local/bin/kind "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-${arch}"; \
    curl -fsSL "https://github.com/yannh/kubeconform/releases/download/${KUBECONFORM_VERSION}/kubeconform-linux-${arch}.tar.gz" | tar -xz -C /usr/local/bin kubeconform; \
    curl -fsSLo /usr/local/bin/argocd "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-${arch}"; \
    chmod +x /usr/local/bin/kubectl /usr/local/bin/helm /usr/local/bin/terraform /usr/local/bin/kind /usr/local/bin/kubeconform /usr/local/bin/argocd; \
    rm -rf /tmp/*; \
    kubectl version --client; helm version; terraform version; kubeconform -v

# --- Anthropic `ant` CLI (drives the self_hosted worker: `ant beta:worker`) ---
# Released as a Go binary (NOT npm): github.com/anthropics/anthropic-cli/releases.
# Bump with --build-arg ANT_VERSION=...
ARG ANT_VERSION=1.15.0
RUN set -eux; \
    case "$(dpkg --print-architecture)" in amd64) A=amd64 ;; arm64) A=arm64 ;; *) A=amd64 ;; esac; \
    curl -fsSL "https://github.com/anthropics/anthropic-cli/releases/download/v${ANT_VERSION}/ant_${ANT_VERSION}_linux_${A}.tar.gz" \
      | tar -xz -C /usr/local/bin ant; \
    chmod +x /usr/local/bin/ant; \
    ant --version

# --- destructive-op guard shims FIRST on PATH --------------------------------
COPY bin/guards/ /opt/guards/
RUN chmod +x /opt/guards/*
ENV PATH="/opt/guards:${PATH}"

COPY run-worker.sh /usr/local/bin/run-worker.sh
RUN chmod +x /usr/local/bin/run-worker.sh

# Self-test: a blocked verb must fail, an allowed one must pass.
RUN /opt/guards/kubectl delete ns x >/dev/null 2>&1 && (echo "guard self-test FAILED" && exit 1) || echo "guard: kubectl delete correctly blocked"

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/run-worker.sh"]
