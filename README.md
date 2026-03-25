# TTFHW — Time To First Hello World

A repeatable, automated benchmarking framework that measures developer experience across four stages: **Learn → Get → Use → Contribute**. Designed for cross-community comparison (CANN, CUDA, ROCm, etc.).

## What is TTFHW?

TTFHW measures how long it takes a new developer to go from zero to their first meaningful contribution in an AI framework community. Unlike one-off user studies, this framework is:

- **Automated** — no human interaction required; runs end-to-end as a script or MCP tool
- **Repeatable** — Docker-standardized environments eliminate machine variation
- **Multi-dimensional** — captures wall-clock time, step counts, error counts, and broken links per stage
- **Comparable** — uniform `community` + `scenario` fields enable cross-framework benchmarking

## Communities

| Directory | Community | Scenario | Status |
|-----------|-----------|----------|--------|
| [`cann/`](./cann/) | Ascend CANN | zero-to-custom-op | ✅ Implemented |

## Repository Structure

```
ttfhw/
├── cann/                        # CANN community implementation
│   ├── runner.py                # Main entry — orchestrates all stages
│   ├── config.yaml              # Runtime config (image version, timeouts, tokens)
│   ├── requirements.txt         # Python dependencies
│   ├── stages/
│   │   ├── base.py              # BaseStage ABC (setup/run/verify/teardown/metrics)
│   │   ├── stage_learn.py       # Stage 1: Discover CANN via search
│   │   ├── stage_get.py         # Stage 2: Pull Docker image, start container
│   │   ├── stage_use.py         # Stage 3: Compile & run AiCPU custom operator
│   │   └── stage_contribute.py  # Stage 4: Submit Issue + PR, track CI
│   ├── metrics/
│   │   └── collector.py         # Unified timing & status collector
│   ├── reports/
│   │   └── reporter.py          # JSON + Markdown report generation
│   ├── fixtures/
│   │   └── custom_op/           # AiCPU AddCustom operator (CPU simulation, no NPU)
│   ├── mcp_server.py            # MCP server (FastMCP)
│   ├── skills/                  # Claude Code skill definitions
│   └── tests/                   # pytest unit tests (32 tests, all mocked)
└── README.md
```

---

## CANN: zero-to-custom-op

Simulates a new developer discovering CANN → pulling the environment → running a custom operator → contributing back to the community.

### The Four Stages

| Stage | What It Measures |
|-------|-----------------|
| **了解 (Learn)** | Search discoverability: official link rank, navigation hops to quickstart, broken links |
| **获取 (Get)** | Environment setup: Docker pull time, image size, setup steps |
| **使用 (Use)** | Developer workflow: operator compile time, run time, compile errors |
| **贡献 (Contribute)** | Community responsiveness: Issue response time, PR CI queue/prepare/run time |

### Quick Start

**Prerequisites:**

```bash
# 1. Install Python dependencies
cd cann
pip install -r requirements.txt

# 2. Configure environment variables
export BING_API_KEY="<your-bing-search-api-key>"   # Azure Cognitive Search key
export GITCODE_TOKEN="<your-gitcode-pat>"           # Permissions: issues:write, pull_requests:write

# 3. Ensure Docker is accessible
sudo usermod -aG docker $USER && newgrp docker
```

**Run all stages:**

```bash
cd cann
python runner.py --stages learn get use contribute --format json
python runner.py --stages learn get use contribute --format markdown
```

**Run a single stage:**

```bash
python runner.py --stages learn --format markdown
python runner.py --stages get use --format json
```

### Output

**JSON report** (machine-readable, for cross-community comparison):

```json
{
  "community": "cann",
  "scenario": "zero-to-custom-op",
  "timestamp": "2026-03-25T10:00:00Z",
  "cann_version": "8.0.RC1",
  "stages": {
    "learn": {
      "status": "pass",
      "search_s": 2.1,
      "official_link_rank": 1,
      "nav_hops": 1,
      "accessible_links": 8,
      "broken_links": 0,
      "errors": []
    },
    "get": {
      "status": "pass",
      "wall_clock_s": 180.5,
      "net_download_s": 165.2,
      "image_size_mb": 8200,
      "setup_steps": 5,
      "errors": []
    },
    "use": {
      "status": "pass",
      "compile_s": 45.1,
      "run_s": 2.3,
      "compile_errors": 0,
      "compile_warnings": 0,
      "run_errors": 0,
      "errors": []
    },
    "contribute": {
      "issue": {
        "status": "pass",
        "submit_s": 1.2,
        "first_response_s": 300,
        "errors": []
      },
      "pr_ci": {
        "status": "pass",
        "submit_s": 2.1,
        "ci_queue_s": 120,
        "ci_prepare_s": 45,
        "ci_run_s": 600,
        "ci_total_s": 768,
        "ci_result": "success",
        "errors": []
      }
    }
  }
}
```

**Markdown report** (human-readable):

```
| 阶段 | 状态 | 关键时间 | 备注 |
|------|------|---------|------|
| 了解 | ✅ pass | 搜索 2.1s，导航 1 跳 | 官方链接排名第1 |
| 获取 | ✅ pass | 总计 180.5s，下载 165.2s | 镜像 8200MB |
| 使用 | ✅ pass | 编译 45.1s，运行 2.3s | 无报错 |
| 贡献-Issue | ✅ pass | 提交 1.2s，首次响应 300s | — |
| 贡献-PR CI | ✅ pass | 排队 120s，运行 600s | CI结果: success |
```

### Configuration (`config.yaml`)

```yaml
cann_image: "ascendhub.huawei.com/public-ascendhub/ascend-toolkit:8.0.RC1"
gitcode_token: "${GITCODE_TOKEN}"   # env var injection
fork_repo: "ttfhw-bot/cann"         # test-dedicated fork for PR submissions
upstream_repo: "ascend/cann"

timeout:
  learn_s: 60
  get_s: 600
  use_s: 300
  issue_response_s: 3600            # polls for first Issue response; null on timeout
  ci_total_s: 7200                  # stops CI polling after 2h; records partial data

on_stage_failure: continue          # continue | abort

search:
  engine: "bing"
  bing_api_key: "${BING_API_KEY}"
  keywords: "Ascend CANN 快速入门"
  official_domains:
    - "gitcode.com/ascend"
    - "hiascend.com"
```

### MCP Server

Start the MCP server to expose the framework as tools for Claude or other MCP clients:

```bash
cd cann
python mcp_server.py
```

Available tools:

| Tool | Description |
|------|-------------|
| `cann_ttfhw_run_all()` | Run all 4 stages, return full report |
| `cann_ttfhw_run_stage(stage, substage?)` | Run one stage (learn/get/use/contribute) |
| `cann_ttfhw_report(format)` | Retrieve last report as JSON or Markdown |

### Claude Code Skills

Install the skill files from `cann/skills/` into your Claude Code config to use one-liners:

| Command | Action |
|---------|--------|
| `/cann-ttfhw` | Run all 4 stages and display report |
| `/cann-learn` | Learn stage only |
| `/cann-get` | Get stage only |
| `/cann-use` | Use stage only |
| `/cann-contribute` | Contribute stage (Issue + PR CI) |
| `/cann-contribute-issue` | Issue sub-stage only |
| `/cann-contribute-pr` | PR CI sub-stage only |

### Tests

```bash
cd cann
pytest tests/ -v
# 32 tests, all dependencies mocked (no Docker, no API keys required)
```

### First Run Results (2026-03-25)

| Stage | Status | Finding |
|-------|--------|---------|
| 了解 (Learn) | ⚠️ warn | Official link ranks **#1** in search; quickstart reachable in **1 hop**; 2 broken doc links (old version URLs returning 404) |
| 获取 (Get) | ❌ fail | `ascendhub.huawei.com` not reachable from external networks; Docker socket permission required |
| 使用 (Use) | ❌ fail | Blocked by Get stage (no container) |
| 贡献 (Contribute) | ❌ fail | Gitcode API path mismatch (uses GitLab `/api/v4/` not Gitee `/api/v5/`); fork repo not yet created |

Full report: [`cann/reports/test-run-2026-03-25.md`](./cann/reports/test-run-2026-03-25.md)

### Environment Requirements

To run all stages successfully:

- [ ] `BING_API_KEY` configured (Azure Cognitive Services — Bing Search v7)
- [ ] Docker accessible (`sudo usermod -aG docker $USER`)
- [ ] Network access to `ascendhub.huawei.com` (Huawei Ascend image registry)
- [ ] `GITCODE_TOKEN` configured with `issues:write` + `pull_requests:write`
- [ ] `ttfhw-bot/cann` fork repository created on Gitcode

---

## Design Principles

1. **Repeatability** — Docker-standardized environment; each run is independently comparable
2. **Extensibility** — `BaseStage` interface means adding a new community (ROCm, CUDA) only requires implementing the same 5-method contract
3. **Multi-dimensional metrics** — time + step count + error count + error messages per stage
4. **Dual output** — JSON for programmatic comparison, Markdown for human reading
5. **Stage isolation** — any stage can be re-run independently; failure defaults to `continue` (configurable)
6. **Idempotency** — all Issue/PR submissions include timestamps in titles to avoid duplicate conflicts

## Stage Status Definition

| Status | Meaning |
|--------|---------|
| `pass` | All success criteria met, no errors |
| `warn` | Core success criteria met, but non-fatal issues exist (e.g. broken links present but quickstart reachable; CI failed but PR submitted successfully) |
| `fail` | Core success criteria not met, or timeout, or unrecoverable error |

## Contributing

To add a new community benchmark (e.g. ROCm):

1. Create a new directory `<community>/`
2. Implement the four stage classes inheriting from `BaseStage`
3. Add `runner.py`, `config.yaml`, `mcp_server.py`, and skill files following the CANN pattern
4. Set `COMMUNITY` and `SCENARIO` constants to enable cross-community report merging
