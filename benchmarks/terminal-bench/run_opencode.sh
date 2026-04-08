#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Configuration — edit these variables
# =============================================================================
N_ATTEMPTS=5                              # Number of attempts per task
N_CONCURRENT=10                           # Number of concurrent trials
MODEL="openrouter/minimax/minimax-m2.7"   # Model identifier
TASKS=(                                   # Task names to run (empty array = all tasks)
  chess-best-move
  circuit-fibsqrt
  compile-compcert
  extract-elf
  git-leak-recovery
  multi-source-data-merger
  path-tracing
  rstan-to-pystan
  sanitize-git-repo
  sparql-university
  sqlite-db-truncate
  torch-tensor-parallelism
)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TIMESTAMP="$(date -u +"%Y-%m-%d__%H-%M-%S")"
JOBS_DIR="${SCRIPT_DIR}/jobs"
RESULTS_DIR="${REPO_ROOT}/results"

# Parse flags (--lpt is on by default; pass --no-lpt to disable)
USE_LPT=true
AGENT_MODE=""
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  case "${ARGS[i]}" in
    --lpt)       USE_LPT=true ;;
    --no-lpt)    USE_LPT=false ;;
    --agent=*)   AGENT_MODE="${ARGS[i]#--agent=}" ;;
    --agent)     AGENT_MODE="${ARGS[i+1]:-}"; ((i++)) || true ;;
  esac
done

# Export OPENCODE_AGENT so opencode_agent.py picks it up
if [[ -n "${AGENT_MODE}" ]]; then
  export OPENCODE_AGENT="${AGENT_MODE}"
fi

# For build-only mode, disable the default plan handoff
if [[ "${AGENT_MODE}" == "build" ]]; then
  export OPENCODE_EXPERIMENTAL_PLAN_MODE=0
fi

# Auto-approve all permissions in headless mode.
# Without this, opencode run auto-rejects permission.asked events,
# which blocks Read/Write/Edit on paths outside the project root
# (e.g., /data/ in Docker containers).
export OPENCODE_PERMISSION='{"*":"allow"}'

# Isolate from local config — only API keys should come from outside the repo.
export OPENCODE_DISABLE_PROJECT_CONFIG=1

# Explicit opencode config for benchmark runs. This is the sole source of
# non-API-key configuration inside the Docker containers.
OPENCODE_CONFIG_CONTENT_JSON=$(cat <<'ENDJSON'
{
  "system": {
    "minimax-m2.7": {
      "label": "MiniMax M2.7",
      "model": "openrouter/minimax/minimax-m2.7",
      "vision": "openrouter/qwen/qwen3.5-397b-a17b",
      "agents": ["build", "plan", "auto"]
    }
  }
}
ENDJSON
)
export OPENCODE_CONFIG_CONTENT="${OPENCODE_CONFIG_CONTENT_JSON}"

# ---------------------------------------------------------------------------
# Resolve harbor command (or harbor_lpt.py wrapper for LPT scheduling)
# ---------------------------------------------------------------------------
resolve_harbor() {
  if [[ "${USE_LPT}" == "true" ]]; then
    if command -v harbor >/dev/null 2>&1; then
      HARBOR_CMD=(python3 "${SCRIPT_DIR}/harbor_lpt.py")
    elif command -v uvx >/dev/null 2>&1; then
      HARBOR_CMD=(uvx --from harbor python3 "${SCRIPT_DIR}/harbor_lpt.py")
    else
      echo "ERROR: Neither 'harbor' nor 'uvx' found on PATH." >&2
      exit 127
    fi
    return
  fi
  if command -v harbor >/dev/null 2>&1; then
    HARBOR_CMD=(harbor)
    return
  fi
  if command -v uvx >/dev/null 2>&1; then
    HARBOR_CMD=(uvx --from harbor harbor)
    return
  fi
  echo "ERROR: Neither 'harbor' nor 'uvx' found on PATH." >&2
  echo "Install the Harbor CLI or uv (uvx) to run this script." >&2
  exit 127
}

# ---------------------------------------------------------------------------
# Build and run
# ---------------------------------------------------------------------------
main() {
  resolve_harbor

  CMD=(
    "${HARBOR_CMD[@]}"
    run
    -d "terminal-bench@2.0"
    --env docker
    --no-force-build
    --no-delete
    --jobs-dir "${JOBS_DIR}"
    -k "${N_ATTEMPTS}"
    -n "${N_CONCURRENT}"
    --agent-import-path "opencode_agent:OpenCodeAudioAgent"
    -m "${MODEL}"
    --artifact /tmp/opencode-output.log
  )

  # Forward API keys
  if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
    CMD+=(--ae "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}")
  fi
  if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    CMD+=(--ae "OPENAI_API_KEY=${OPENAI_API_KEY}")
  fi
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    CMD+=(--ae "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}")
  fi

  # Forward OpenCode agent configuration env vars
  if [[ -n "${OPENCODE_AGENT:-}" ]]; then
    CMD+=(--ae "OPENCODE_AGENT=${OPENCODE_AGENT}")
  fi
  if [[ -n "${OPENCODE_EXPERIMENTAL_PLAN_MODE:-}" ]]; then
    CMD+=(--ae "OPENCODE_EXPERIMENTAL_PLAN_MODE=${OPENCODE_EXPERIMENTAL_PLAN_MODE}")
  fi
  if [[ -n "${OPENCODE_PERMISSION:-}" ]]; then
    CMD+=(--ae "OPENCODE_PERMISSION=${OPENCODE_PERMISSION}")
  fi
  if [[ -n "${OPENCODE_CONFIG_CONTENT:-}" ]]; then
    CMD+=(--ae "OPENCODE_CONFIG_CONTENT=${OPENCODE_CONFIG_CONTENT}")
  fi
  CMD+=(--ae "OPENCODE_DISABLE_PROJECT_CONFIG=1")

  # Task filters
  if [[ ${#TASKS[@]} -gt 0 ]]; then
    for task in "${TASKS[@]}"; do
      CMD+=(-i "${task}")
    done
  fi

  echo "==> Running OpenCode Audio agent on terminal-bench@2.0"
  echo "    Model:       ${MODEL}"
  echo "    Attempts:    ${N_ATTEMPTS}"
  echo "    Concurrency: ${N_CONCURRENT}"
  echo "    Tasks:       ${TASKS[*]:-ALL}"
  echo "    Agent mode:  ${AGENT_MODE:-default (plan-build-eval)}"
  echo "    LPT:         ${USE_LPT}"
  echo ""

  # Run from script dir so Python can import opencode_agent
  (cd "${SCRIPT_DIR}" && "${CMD[@]}")

  # Copy results to top-level results/
  LATEST_JOB="$(ls -td "${JOBS_DIR}"/*/ 2>/dev/null | head -1)"
  if [[ -n "${LATEST_JOB}" ]]; then
    SUFFIX="opencode"
    [[ -n "${AGENT_MODE}" ]] && SUFFIX="opencode-${AGENT_MODE}"
    DEST="${RESULTS_DIR}/terminal-bench-${SUFFIX}-${TIMESTAMP}"
    mkdir -p "${DEST}"
    cp -r "${LATEST_JOB}"/* "${DEST}"/
    echo ""
    echo "==> Results copied to ${DEST}"
  fi
}

main "$@"
