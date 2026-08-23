# Manual validation pass — older Mac

Purpose: first real-device test outside the dev machine. Confirms Phase 0
stability before cross-platform work (Phase 1) builds on it.

## What we learn from YOUR machine

1. Does packaging work on an older macOS + older Python?
2. Is the unknown-chip / non-Apple-Silicon path honest (no fantasy numbers)?
3. Do emitted launch commands actually run?

## Protocol (~10 minutes)

```bash
# 1. Get python 3.10+ (if `python3 --version` < 3.10, install from python.org or brew)
python3 --version

# 2. From a clone of the repo:
cd beanfit
PYTHONPATH=src python3 -m unittest discover -s tests   # expect: OK

# 3. Run the tool three ways and save output:
PYTHONPATH=src python3 -m beanfit                       > out-table.txt
PYTHONPATH=src python3 -m beanfit --use-case coding     >> out-table.txt
PYTHONPATH=src python3 -m beanfit --json                > out-json.txt
```

4. If Ollama is installed, run the "Pick" command the tool prints, then
   `/verbose` inside the session — paste the real tok/s into results.
5. Send back: macOS version, chip ("About This Mac"), RAM, the two output
   files, and the verbose tok/s if you ran step 4.

## Expected behavior on an Intel (non-Apple-Silicon) Mac

- Header shows `[non-Apple-Silicon: estimates unreliable]` and `[BW unknown fallback]`
- Speed estimates carry ±50% bands and are expected to be WRONG in your favor
  of skepticism — treat them as ordering hints only
- MLX alternative line will not help you (MLX is Apple-Silicon-only); this is
  known and handled properly in Phase 1/2

## Pass criteria

- [ ] Unit tests pass on the machine
- [ ] No crash on any of the three invocations
- [ ] JSON parses (`python3 -m json.tool out-json.txt`)
- [ ] Estimates flagged as unreliable, not presented confidently
