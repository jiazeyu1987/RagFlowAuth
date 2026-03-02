# Repository Guidelines

## Project Structure & Module Organization
`backend/` contains the FastAPI service, database schema, business services, and `backend/tests/` unit tests. `fronted/` contains the React app, shared UI code, Playwright tests in `fronted/e2e/`, and static assets in `fronted/public/`. Deployment and maintenance tooling live in `docker/`, `scripts/`, and `tool/`. Project docs and test reports are under `doc/`.

## Build, Test, and Development Commands
Backend setup:
```powershell
pip install -r backend/requirements.txt
python -m backend init-db
python -m backend
```
This installs dependencies, initializes the local SQLite auth DB, and starts the API.

Frontend setup:
```powershell
cd fronted
npm install
npm start
```
This installs the React dependencies and starts the dev server.

Key test commands:
```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
cd fronted; npm run e2e:all
powershell -File scripts/run_fullstack_tests.ps1
```
Use the last command for the combined backend + frontend report in `doc/test/reports/`.

## Coding Style & Naming Conventions
Follow existing style in touched files. Python uses 4-space indentation, `snake_case` for functions/modules, and `PascalCase` for classes. React components and page files use `PascalCase`; hooks and utilities use `camelCase`. Keep API modules grouped by feature, for example `backend/app/modules/knowledge/` and `fronted/src/features/knowledge/`. No dedicated formatter config is checked in, so keep imports tidy and changes minimal.

## Testing Guidelines
Backend tests use `unittest` and are named `test_*.py`. Frontend end-to-end coverage uses Playwright specs named `*.spec.js`. Add tests next to the area you change, and prefer focused unit coverage for backend service logic plus Playwright coverage for user-visible flows. Update or regenerate the fullstack report when validating broad changes.

## Commit & Pull Request Guidelines
Recent history uses short, imperative commit subjects, often in Chinese, such as `修复审核问题` or `批量上传`. Keep subjects brief and specific. Pull requests should describe the functional change, list validation commands run, note config or migration impact, and include screenshots for UI changes.

## Security & Configuration Tips
Do not commit secrets. Keep local runtime settings in `ragflow_config.json` and verify service URLs before testing integrations. Treat `data/` as local environment state, not source-controlled feature code.
