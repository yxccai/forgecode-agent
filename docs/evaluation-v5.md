# V5 evaluation results

Completed runs: 40 / 40.
Model: `qwen3.7-flash`. Reasoning effort: `None` (null means provider default).
Dataset SHA-256: `d6497935aedb8826d4db5595a5bb01cc02216309cc09bf7668d9aad29064acd3`.

## Aggregate metrics

| Variant | N | Task success | Test pass | Steps | Tools | Tokens | Seconds | Files read |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 20 | 100.0% | 100.0% | 5.90 | 5.40 | 15367 | 37.95 | 2.00 |
| no_planning | 5 | 100.0% | 100.0% | 5.00 | 5.60 | 12590 | 14.45 | 2.00 |
| no_context | 5 | 100.0% | 100.0% | 6.60 | 5.60 | 14090 | 39.66 | 2.00 |
| no_verification | 5 | 100.0% | 100.0% | 6.40 | 5.40 | 16178 | 44.04 | 2.00 |
| no_memory | 5 | 100.0% | 100.0% | 5.80 | 5.80 | 13813 | 40.78 | 2.00 |

Full uses 20 tasks; ablations use the same fixed 5-task subset. Do not directly compare unpaired means.

## Paired differences

Deltas are ablation minus full on matching task/repeat pairs.

| Variant | Pairs | Success delta | Token delta | Seconds delta |
|---|---:|---:|---:|---:|
| no_planning | 5 | +0.0% | -814 | -24.76 |
| no_context | 5 | +0.0% | +686 | +0.46 |
| no_verification | 5 | +0.0% | +2775 | +4.83 |
| no_memory | 5 | +0.0% | +409 | +1.58 |

## Per-run outcomes

| Task | Variant | Success | Tests | Failure | Tokens | Seconds |
|---|---|---|---|---|---:|---:|
| balanced | full | True | 4/4 | - | 13106 | 42.96 |
| balanced | no_context | True | 4/4 | - | 12920 | 40.50 |
| balanced | no_memory | True | 4/4 | - | 13600 | 32.81 |
| balanced | no_planning | True | 4/4 | - | 15381 | 19.70 |
| balanced | no_verification | True | 4/4 | - | 14645 | 46.00 |
| binary_search | full | True | 4/4 | - | 13264 | 41.64 |
| binary_search | no_context | True | 4/4 | - | 12797 | 40.55 |
| binary_search | no_memory | True | 4/4 | - | 15735 | 40.22 |
| binary_search | no_planning | True | 4/4 | - | 12516 | 14.96 |
| binary_search | no_verification | True | 4/4 | - | 15120 | 47.98 |
| chunks | full | True | 3/3 | - | 12940 | 32.54 |
| clamp | full | True | 4/4 | - | 15224 | 33.47 |
| counts | full | True | 3/3 | - | 12332 | 35.17 |
| factorial | full | True | 3/3 | - | 21903 | 47.14 |
| flatten | full | True | 3/3 | - | 23535 | 55.84 |
| invert | full | True | 2/2 | - | 15312 | 35.25 |
| is_prime | full | True | 5/5 | - | 16324 | 43.35 |
| median | full | True | 3/3 | - | 12722 | 35.28 |
| median | no_context | True | 3/3 | - | 14282 | 35.07 |
| median | no_memory | True | 3/3 | - | 14392 | 41.89 |
| median | no_planning | True | 3/3 | - | 9628 | 10.44 |
| median | no_verification | True | 3/3 | - | 14813 | 39.08 |
| merge_intervals | full | True | 3/3 | - | 13475 | 43.05 |
| merge_intervals | no_context | True | 3/3 | - | 15769 | 42.17 |
| merge_intervals | no_memory | True | 3/3 | - | 12440 | 47.69 |
| merge_intervals | no_planning | True | 3/3 | - | 13550 | 15.30 |
| merge_intervals | no_verification | True | 3/3 | - | 22524 | 51.51 |
| palindrome | full | True | 3/3 | - | 11461 | 23.19 |
| refactor_join | full | True | 3/3 | - | 14499 | 32.21 |
| refactor_sum | full | True | 3/3 | - | 14452 | 33.09 |
| refactor_sum | no_context | True | 3/3 | - | 14683 | 40.01 |
| refactor_sum | no_memory | True | 3/3 | - | 12897 | 41.31 |
| refactor_sum | no_planning | True | 3/3 | - | 11874 | 11.85 |
| refactor_sum | no_verification | True | 3/3 | - | 13790 | 35.62 |
| rotate | full | True | 4/4 | - | 16838 | 50.03 |
| running_total | full | True | 3/3 | - | 11067 | 18.95 |
| slug | full | True | 3/3 | - | 12280 | 33.26 |
| sum | full | True | 3/3 | - | 22306 | 46.45 |
| transpose | full | True | 3/3 | - | 14793 | 34.55 |
| unique | full | True | 3/3 | - | 19502 | 41.62 |

## Interpretation limits

Corrected reruns: 5. The first no-verification pilot omitted the task-level test reminder; corrected runs use exactly the same task prompt as full. Both raw datasets remain local.
These are authored, small Python tasks with 24 distractor modules, not a production-repository benchmark.
One repeat and five paired tasks per ablation cannot establish statistical significance or broad superiority.
Memory is standardized source-backed repository orientation, not recalled hidden answers or natural longitudinal task history.
No-verification disables the runtime's mandatory baseline/final repair loop; the model may still choose test tools.
Latency includes network and concurrent API scheduling. Token counts come from provider usage, not local estimates.
Failures are classified conservatively: code_or_edit, verification, termination, verification_tampering, infrastructure.
A successful verifier proves the supplied cases passed, not general correctness or security sandboxing.
