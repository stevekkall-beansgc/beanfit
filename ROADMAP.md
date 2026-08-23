# beanfit ROADMAP — v0.1 prototype → product

Created: 2026-08-23 · Ledger of record for external commitments:
[BeanLabs/BETS.md](https://github.com/stevekkall-beansgc/beanfit) · Effort keys:
S <1d · M 1–3d · L 3–10d

---

## 1. Where we are (v0.1 inventory)

Works: single-file stdlib CLI · Apple Silicon detection (chip, RAM, Metal
working-set cap) · static 9-model catalog · ranked table + JSON · launch
commands (Ollama + MLX alt).

Honest gaps (incl. meta-review findings):

- 3/9 catalog tags 404'd on ollama.com; #1 coding pick emitted a dead pull tag
- Speed numbers are family-table estimates, no uncertainty bands
- macOS-only detection (sysctl/Metal hardcoded)
- No packaging, tests, or CI
- No `beanfit init`, no beacon, no drift-watch — i.e., none of the layers the
  council identified as the actual product

## 2. Value proposition (the thing this roadmap must earn)

**One-liner:** beanfit turns "what can my machine run?" into *"your machine's
entire local-AI stack — model × quant × runtime × context × agent-tooling
config — generated, installed, and kept current."*

**Three-rung ladder** (each rung is a phase below):

| Rung | Promise | Status |
|------|---------|--------|
| 1. ANSWER | "What runs well on THIS device?" — ranked, honest, <5s | ✅ v0.1 (Mac only) |
| 2. DO | "`beanfit init` writes my opencode.jsonc, sizes my sub-agent models, fixes num_ctx" | 🚧 Phase 3 |
| 3. MAINTAIN | "Your stack upgrades itself when better models land — and you can prove what runs where" | 🚧 Phases 4–5 |

**Who it's for:**

1. Developers running agents/local LLMs on *heterogeneous* hardware (not
   everyone has a Max/Ultra) who currently hand-tune dotfiles per machine.
2. Teams standardizing local inference who need device-appropriate profiles
   shared and enforced — eventually with a compliance/audit artifact.

**Why cross-platform is strategy, not a feature checklist:**

- Fit-checking is commoditized; the uncontested layer is whole-stack config +
  maintenance. That layer is only credible if it works wherever the stack runs.
- Our queued content bets (BF-P2 pre-purchase SKU advisor, BF-P3 Strix Halo /
  DGX Spark beachhead) live on **non-Apple hardware** — expansion unlocks them.
- Team/compliance buyers own mixed fleets by definition.
- Runtime vendors will absorb single-platform recommenders first (council
  death-scenario); breadth delays that.

## 3. Phases

### Phase 0 — Productize the core (week 1)

Prereq for everything; no behavior change beyond packaging.

- [ ] **T0.1** Package: `pyproject.toml`, `beanfit` console entry point,
      pipx/uv install path; keep zero-arg default UX. *(S)*
- [ ] **T0.2** Split monolith into modules: `hw/`, `catalog/`, `engine/`,
      `emit/`. *(S)* Deliberately supersedes the prototype-era "single-file
      bias" (SESSION-BRIEF convention) — cross-platform detectors don't fit
      one file; stdlib-only stays.
- [ ] **T0.3** Test suite: golden-output fixtures per chip profile; CI matrix
      macos/arm64 + ubuntu + windows (red now → green as phases land). *(M)*
- [ ] **T0.4** Catalog integrity gate: release script validates every
      ollama/HF tag against the registry; CI fails on dead tags (kills the
      meta-review bug class permanently). *(S)*
- [ ] **T0.5** Estimator honesty v1: ±% bands in output, assumptions exposed
      in `--json`; spike direct Metal-limit read (paddock-style) as follow-up. *(M)*

### Phase 1 — Any device, any accelerator (weeks 2–4)

Headline ask. Everything hangs off a new abstraction:

- [ ] **T1.1** `DeviceProfile` schema: `{os, arch, backend: unified|discrete|cpu,
      usable_mem_gib, mem_bandwidth_gbs, accelerators[], estimate_flags}` —
      engine consumes profiles ONLY (no platform ifs in scoring). *(M)*
- [ ] **T1.2** Linux detector: `/proc/meminfo` + `lspci`; `nvidia-smi`,
      `rocm-smi` classification. *(M)*
- [ ] **T1.3** Windows detector: psutil/WMI + `nvidia-smi.exe` discovery. *(M)*
- [ ] **T1.4** Discrete-GPU budget model: fit-in-VRAM vs layer-offload penalty
      curve — honest "fits but crawls" verdicts instead of binary yes/no. *(L)*
- [ ] **T1.5** GPU spec tables: RTX 50/40, RX 9000/7000, Arc (VRAM + bandwidth);
      unknown SKUs fall back flagged as estimates. *(M)*
- [ ] **T1.6** CPU-only path: RAM budget + realistic low tok/s (no fantasy
      numbers; honesty policy applies hardest here). *(S)*
- [ ] **T1.7** Unified-memory non-Apple: Snapdragon X / Copilot+ class,
      Jetson Orin, Pi 5 — small-model catalog tier. *(M, stretch)*

*Acceptance:* identical ranked-table UX on M-series, RTX laptop (Win),
Linux+NVIDIA box; CI green on all three OSes.

### Phase 2 — Runtime neutrality (weeks 3–5, overlaps Phase 1)

- [ ] **T2.1** Runtime capability matrix: MLX=macOS-only, vLLM=CUDA-first,
      llama.cpp/LM Studio/Ollama=cross-platform; recommendation filtered by
      what EXISTS on the detected platform. *(M)*
- [ ] **T2.2** Launch-command emitters per runtime incl. correct context flags
      (`num_ctx`, `llama-server -c`, mlx_lm args). *(S)*
- [ ] **T2.3** Quant-format mapping per backend (GGUF q4_K_M / MLX 4bit /
      AWQ-GPTQ on CUDA) — right format per runtime, not GGUF everywhere. *(M)*
- [ ] **T2.4** Installed-runtime detection: recommend what the user can run
      tonight; offer one-line install for the rest. *(S)*

### Phase 3 — `beanfit init`: the actual product (weeks 4–8)

Council quote is the spec: *"I don't want another table — I want `beanfit
init` to write my opencode.jsonc, size my sub-agent models, and tell me when
Qwen3.7 obsoletes my setup."* This phase IS bet B1' (coordinate with Agency
tasks #23/#24 — don't double-build).

- [ ] **T3.1** `beanfit init` flow: detect → confirm use-case → show stack
      plan → write configs; opt-in beacon inside this flow per
      `shared/telemetry/CONTRACT.md`. *(L)*
- [ ] **T3.2** Config writers: Ollama pulls · LM Studio hint · `mcp.json`
      sizing block · `opencode.jsonc` block (num_ctx + sub-agent model tiers)
      · Claude Code settings. *(L)*
- [ ] **T3.3** Safe patching: idempotent, diff-preview, auto-backup, never
      clobber user keys. *(M)*
- [ ] **T3.4** `beanfit doctor`: probe the emitted config end-to-end, report
      measured tok/s vs estimate (feeds accuracy moat, catches regressions). *(M)*
- [ ] **T3.5** Funnel instrumentation matching B1' signal definition exactly:
      install → config-generated ≤48h; day-14 re-report. Off by default;
      privacy doc updated BEFORE shipping. *(M)*

**Signal gate (BETS.md B1', day 75):** ≥25% of installs generate a config
≤48h AND ≥15% re-report at day 14. Below either bar → reposition per ledger
(content/SEO play); Phases 4–5 descope accordingly.

### Phase 4 — Retention: drift-watch + ground truth (weeks 6–12)

- [ ] **T4.1** Catalog sync automation (registries → normalized catalog →
      human review queue) — make the council's "0.5 FTE forever" tax cheap. *(L)*
- [ ] **T4.2** Scheduled re-fit / `beanfit refit`: "a better model for YOUR
      machine landed" digest (local notification or email opt-in). *(M)*
- [ ] **T4.3** Opt-in benchmark contributions → community tok/s percentiles
      per (device, model, quant) — the data network effect, only meaningful
      post-cross-platform. *(L)*

### Phase 5 — Value capture (months 3–6, gated on Phase 3 signal)

- [ ] **T5.1** Landing page + SEO wave 1: device×use-case pages; then BF-P2
      SKU advisor + BF-P3 Strix Halo/DGX Spark pages (both need Phase 1). *(M)*
- [ ] **T5.2** Compliance wedge validation FIRST: 5 design-partner
      interviews; only then build team-profiles MVP (org profile YAML +
      `beanfit audit` local-only-inference report). *(M interview, L build)*
- [ ] **T5.3** Scenario doc: p50/p90 ARR table with sourced conversion norms
      or HYPOTHESIS flags (council-required fix; unblocks any raise talk). *(S)*
- [ ] **T5.4** Decision gate @ month 6: standalone company vs portfolio
      feature (deliberately-unresolved council item; owner: Steve). Kill
      criterion stands: <500 WAU at month 6 → fold.

## 4. Explicitly out of scope (v1)

Hosting inference · GPU cloud brokering · phones/tablets (runtime ecosystem
immature; revisit when llama.cpp-class stacks ship there) · becoming a
runtime ourselves.

## 5. Sequencing summary

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► GATE (day-75 signal) ──► Phase 4/5
 pack       any device   runtimes    beanfit init        │
            any GPU                  (B1' funnel)        ├─ pass ► retention + revenue
            │                                            └─ fail ► content/SEO reposition
            └── T1.5+T1.7 unblock BF-P2/P3 content bets immediately
```

Cheapest learning per dollar stays true: Phase 0–1 are $0; the only paid item
in the near term remains Agency task #21 ($15 domain) — no new spend proposed
by this roadmap.
