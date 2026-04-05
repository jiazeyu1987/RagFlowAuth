# Real Data E2E (RAGFlow)

## Scope
- `@realdata` tests validate real managed `data/` paths for:
  - Smart chat (`/chat`)
  - Global search (`/agents`)

## Run
- Non-strict (environment not ready -> may `skip`):
  - `npm run e2e:realdata`
- Strict (environment not ready -> `fail`):
  - `npm run e2e:realdata:strict`
- Full e2e chain now runs:
  - non-integration regression/smoke
  - non-realdata integration
  - strict realdata integration
  - `npm run e2e`

## Config
- `E2E_REAL_CHAT_NAME`: target chat name (default: `展厅聊天`)
- `E2E_REAL_CHAT_PROMPTS`: comma-separated prompts for multi-turn chat
- `E2E_REAL_SEARCH_TERMS`: comma-separated search terms (highest priority)
- `E2E_REAL_SEARCH_TERMS_FILE`: line-based term file path  
  default: `fronted/e2e/fixtures/ragflow_real_search_terms.txt`
- `E2E_REAL_MAX_TERMS`: max terms to verify in matrix test (default: `3`)
- `E2E_REAL_MIN_HIT_TERMS`: minimum terms that must have hits (default: `2`)
- `E2E_REAL_MIN_ANSWER_CHARS`: minimum assistant answer length (default: `8`)

## Notes
- Search matrix test pre-checks terms through `/api/search` and only executes UI checks for terms with hits.
- Playwright report annotations include selected terms and the term-file path.
- `npm run e2e:realdata:strict` internally sets `E2E_REQUIRE_REAL_FLOW=1` via `scripts/run_realdata_e2e.py`.
