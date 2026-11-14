.PHONY: all data test site e2e
all: data site                     ## full refresh + site build
data:                              ## sources -> warehouse -> QA gate -> forecasts -> site data
	uv run pricelens all
test:                              ## every test: pipeline, browser maths, smoke
	uv run ruff check src tests && uv run pytest
	cd app && npx tsc -b && npm run lint && npm test && npm run build && npm run e2e
site:                              ## static site -> app/dist
	cd app && npm run build
