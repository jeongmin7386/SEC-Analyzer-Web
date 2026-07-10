# KR·US Stock Analyzer

FastAPI + React web app for analyzing US stocks with SEC EDGAR data and Korean stocks with OpenDART data. The repository name can remain SEC-Stock-Analyzer, while the service display name is now separated as `KR·US Stock Analyzer`.

This project is for research and education only. It is not investment advice.

## Supported Markets

- US stocks: SEC EDGAR `company_tickers.json` and `companyfacts`
- Korean stocks: OpenDART annual financial statements
- Market indices: S&P 500, Nasdaq Composite, Dow Jones, KOSPI, KOSDAQ, KOSPI 200
- Exchange rates: USD/KRW, JPY/KRW, EUR/KRW
- ETF API from the prior version is retained, but the main navigation focuses on stock analysis, indices, and FX.

## Architecture

```text
backend/
  main.py
  app/
    providers/
      base_provider.py
      sec_provider.py
      opendart_provider.py
    services/
      market_resolver.py
      stock_search_service.py
      stock_analysis_service.py
    analysis_presets.py
    metric_calculator.py
    opendart_accounts.py
    stock_master.py
    sec_client.py
    market_data.py
    cache.py
frontend/
  src/
    components/
      StockAnalysisPage.jsx
      IndexPage.jsx
      ExchangePage.jsx
```

Responsibilities are split into search, market resolution, market-specific providers, normalized financial conversion, metric calculation, score calculation, and UI rendering.

## Market Resolution

`GET /api/stocks/search?q={query}&market=AUTO|KR|US` searches a real stock master source before returning candidates.

Rules:

- Six-digit numeric codes are treated as Korean stock candidates.
- `.KS` and `.KQ` suffixes are treated as Korean stocks.
- English tickers are treated as US candidates, but AUTO can still return Korean name matches.
- Company-name searches use master data rather than regex-only resolution.
- If results are ambiguous, the frontend shows a selection list instead of choosing automatically.

Normalized stock shape:

```json
{
  "market": "KR",
  "symbol": "005930",
  "displaySymbol": "005930",
  "companyName": "삼성전자",
  "exchange": "KOSPI",
  "currency": "KRW",
  "corpCode": "00126380"
}
```

## SEC Data

US analysis keeps the existing SEC EDGAR CompanyFacts flow. The frontend never calls SEC directly; backend `SECProvider` wraps the existing `SECClient`.

SEC requests:

- use `requests.Session()` when available
- include `User-Agent`
- wait at least 0.2 seconds between SEC requests
- cache companyfacts JSON for 24 hours
- call companyfacts once per company and calculate all metrics from that JSON

## OpenDART Data

Korean analysis uses OpenDART `fnlttSinglAcntAll.json`.

Behavior:

- CFS 연결재무제표 is requested first.
- OFS 별도재무제표 is used only when CFS is unavailable.
- Account mapping is separated in `backend/app/opendart_accounts.py`.
- Standard XBRL account IDs are preferred, then aliases, then normalized account names.
- Missing fields become `INSUFFICIENT_DATA` instead of automatic failure.

The current Korean stock master is a small local starter list for Samsung Electronics, SK hynix, Kakao, NAVER, and Hyundai Motor. It is structured so it can be replaced by cached OpenDART corp_code master data later.

## Metrics And Scoring

Common metrics:

- Net profit margin = net income / revenue
- Net income growth = YoY net income growth
- Debt ratio = liabilities / equity
- Current ratio = current assets / current liabilities
- ROE = net income / equity
- Share issuance growth = absolute YoY share count growth
- EPS growth = YoY EPS growth

Metric status:

- `PASS`
- `FAIL`
- `INSUFFICIENT_DATA`

Default thresholds:

- Net profit margin >= 20%
- Net income growth >= 10%
- Debt ratio < 75%
- Current ratio >= 100%
- ROE >= 25%
- Share issuance growth < 10%
- EPS growth >= 7.5%

Presets are in `backend/app/analysis_presets.py`: default, Korean market, US growth, and custom.

## API

Legacy endpoints remain:

- `POST /api/analyze/stock`
- `GET /api/analysis/{ticker}`
- `POST /api/analyze/etf`
- `POST /api/etf-analysis`

Unified stock endpoints:

- `GET /api/stocks/search?q={query}&market=AUTO|KR|US`
- `GET /api/stocks/{market}/{symbol}/profile`
- `GET /api/stocks/{market}/{symbol}/financials`
- `GET /api/stocks/{market}/{symbol}/prices`
- `POST /api/stocks/analyze`

Example:

```json
{
  "market": "KR",
  "symbol": "005930",
  "presetId": "kr-market",
  "years": 10,
  "includePrice": true,
  "pricePeriod": "1y"
}
```

Response includes company profile, market, currency, data source, as-of date, normalized financials, metrics, score, warnings, missing fields, price history, and cache metadata.

## Cache

File cache is used instead of requiring Redis:

- SEC companyfacts: `backend/cache/companyfacts`
- OpenDART financial statements: `backend/cache/opendart`
- yfinance timezone cache: `backend/cache/yfinance`, with temp fallback if needed

Cache TTL defaults to 24 hours for SEC and OpenDART financial data.

## Environment

Create `.env` from `.env.example`.

```text
SEC_USER_AGENT=
SEC_CONTACT_EMAIL=
OPENDART_API_KEY=
STOCK_PRICE_API_KEY=
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Do not commit real API keys.

## Run Locally

Backend:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
pnpm install
pnpm dev
```

For local frontend development:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Tests

Backend:

```powershell
cd backend
python -m unittest discover -s tests
python -m py_compile main.py app\*.py app\providers\*.py app\services\*.py
```

Frontend:

```powershell
cd frontend
pnpm build
```

## Deployment

The project includes `Dockerfile` and `render.yaml`. Configure the environment variables on the deployment platform. For Korean stock analysis, `OPENDART_API_KEY` is required at runtime.

## Data Limitations

- SEC does not provide Korean stock financials.
- OpenDART does not provide a simple US-style ticker API.
- Current Korean stock master data is a starter list and should be replaced by a cached full corp_code master for production.
- Yahoo Finance via yfinance can be delayed or temporarily unavailable.
- OpenDART and SEC rate limits can affect first-time uncached analysis.
- Price data is shown as recent trading-day data, not guaranteed real-time data.
- This tool is not investment advice.
