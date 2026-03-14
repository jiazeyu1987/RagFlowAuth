# SEC-DLP-BENCH-001 Report

- Generated at: 2026-03-14 03:41:20
- Verdict: **PASS**
- false_allow_rate: 0.0 (threshold <= 0.1)
- false_block_rate: 0.0 (threshold <= 0.1)

| Case | Expected | Actual | Pass | Level | Masked | Model | Reason |
|---|---|---|---|---|---|---|---|
| high_sensitive_should_block | block | block | YES | high | True | qwen-plus | egress_blocked_high_sensitive_payload |
| non_whitelist_model_should_block | block | block | YES | none | False | gpt-4 | egress_blocked_model_not_allowed:gpt-4 |
| whitelist_model_should_allow | allow | allow | YES | none | False | qwen-plus |  |
| masked_but_allow | allow | allow | YES | medium | True | qwen-plus |  |

