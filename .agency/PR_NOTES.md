## What
Update text trial ordering to Qwen3.5 2B, hold the failed LFM1.2B text configuration, synchronize catalog mirrors and include the historical evidence behind those descriptions. Advance source identity to 0.8.1.

## Why
Users currently see a first suggestion whose tested text configuration failed factual acceptance. Suggestions need to reflect that evidence while the newer candidate still awaits complete phone qualification.

## Risk
These are comparison suggestions, not memory-fit or production guarantees. All models remain unqualified and selection remains empty. Runtime/device/artifact pins and non-text task ordering stay intact. The native generation integration is excluded.

## Test
Canonical unit/offline checks, native metadata contracts, generated snapshot equality, registry metadata validation and exact-source companion acceptance are required. Existing Mac ranking goldens remain unchanged; final CI/release proof is attached to the exact merged commit.

## Review-focus
Check failed-configuration precedence, readable experience-specific labels, evidence references and preserved phone qualification holds. Publish this canonical catalog with the matching web snapshot; do not include the separate native pilot branch.
