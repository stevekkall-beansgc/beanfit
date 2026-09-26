# Offline mobile qualification demo

All data and measurements here are fictional. No model or iPhone is benchmarked.
The three candidates illustrate a tiny model failing quality, a smaller passing
model, and a larger passing model. Synthetic data never produces a real winner.

```sh
PYTHONPATH=src python3 -m beanfit mobile \
  --profile examples/mobile/profile.synthetic.json \
  --receipts examples/mobile/receipts.synthetic.json
python3 scripts/mobile_demo.py
```

Expect `needs_device_evidence` and `selection: null`. The two larger fictional
candidates have `passes_demo_gates: true`. The owned E2E verifies those outcomes.
Unit tests model physical-receipt policy entirely with synthetic test inputs;
they are not saved as physical measurement evidence.

A real product profile uses the same shape, with its approved dataset hash,
critical cases, repeats, limits and memory method. Supply raw reviewed receipts
from the target phone. Each candidate needs an exact model/quant revision and
runtime revision, source evidence reference and matched workload metadata.
`stack_id` must distinguish text-only from speech/retrieval-enabled products.
`latency_ms` uses the product-defined timing boundary, held constant by the
pinned workload and stack. `peak_stack_bytes` includes the maximum attributable
incremental memory during load, prefill and inference (plus concurrent product
components), not just final RSS or weight file size. Apple-managed allocations
must not be silently excluded. The selector does not collect these measurements.

See [requirements and remaining device gate](../../experiments/iphone/REQUIREMENTS.md).
