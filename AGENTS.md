# AGENTS.md — beanfit

CLI that tells you what local AI actually fits — and runs well — on THIS
Mac. Detection → fit engine → honest emission.

## Layout
- `src/beanfit/hw/` — hardware detect (`detect() -> DeviceProfile`),
  bandwidth table, budget math.
- `src/beanfit/engine/` — estimate (tok/s + honesty bands) and evaluate
  (ranking score).
- `src/beanfit/catalog/` — pinned model metadata + live registry validator.
- `src/beanfit/emit/` — table/json renderers, launch command builder.

## Test commands
- All: `PYTHONPATH=src python3 -m unittest discover -s tests`
- Golden scores are load-bearing: `tests/test_evaluate.py` pins ranking
  output (121.8 et al). Never "update" a golden number to make a change pass.

## Honesty rules (the product IS these)
- "Always pin, never guess" — catalog MLX repos are hand-pinned; heuristics
  may WARN, never claim spec_sheet.
- Every estimate ships its uncertainty band; budgets carry an assumptions()
  block. Weakening or faking either is a rejected PR regardless of tests.
- Non-Apple-Silicon output must contain no fantasy numbers (no unified-
  memory caps on Intel).

## Catalog edits
Any new row needs: verified ollama tag, pinned HF/MLX repo (or explicit
omit decision recorded in `models.py` comments), measured q4/q8 GiB.
`catalog/validate.py` fails the build on dead pins (401 counts as dead).

## Known debt
Audit findings in `~/beans/labs/beanlabs/AUDIT-2026-08/findings/BF-*.md`:
NamedTuple catalog rows, assumptions()-from-constants, Intel cap gating,
exact-pin bandwidth lookup.

## Review rules
Binding contract lives in `~/beans/platform/qa-kit/README.md`. Done =
`python3 ~/beans/platform/qa-kit/bin/run_all.py --only beanfit --all` green.
