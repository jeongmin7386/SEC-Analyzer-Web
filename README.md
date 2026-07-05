# SEC Stock Analyzer Web

FastAPI + React web app for SEC EDGAR `companyfacts` based stock analysis and ETF holdings based analysis.

## Project Structure

```text
.
├─ backend/
│  ├─ main.py
│  ├─ requirements.txt
│  ├─ cache/
│  │  └─ companyfacts/
│  └─ app/
│     ├─ analyzer.py
│     ├─ cache.py
│     ├─ etf_analyzer.py
│     ├─ etf_holdings.py
│     ├─ market_data.py
│     ├─ schemas.py
│     ├─ sec_client.py
│     └─ split_adjustment.py
├─ frontend/
│  ├─ package.json
│  └─ src/
├─ Dockerfile
└─ render.yaml
```

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

For local frontend development, set `frontend/.env`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## API

### Stock Analysis

`POST /api/analyze/stock`

Input:

```json
{ "ticker": "AAPL" }
```

Output includes company profile, annual rows, metric scores, final score, verdict, warnings, and `cache` metadata.

The legacy endpoint `GET /api/analysis/{ticker}` is kept for compatibility.

### ETF Analysis

`POST /api/analyze/etf`

Input:

```json
{ "ticker": "QQQ" }
```

Manual holdings fallback:

```json
{
  "ticker": "CUSTOM",
  "manualHoldings": "AAPL:7.5, MSFT:7.2, NVDA:6.8"
}
```

Output includes top holding analysis rows, simple average score, holding-weighted average score, final verdict, and cache metadata per holding.

The legacy endpoint `POST /api/etf-analysis` is kept for compatibility.

## Stock Scoring

The backend calls SEC `companyfacts` once per company and calculates all metrics from that JSON.

Metrics:

- Net profit margin = `NetIncomeLoss / Revenue`
- Net income growth = year-over-year growth of `NetIncomeLoss`
- Debt ratio = `Liabilities / StockholdersEquity`
- Current ratio = `AssetsCurrent / LiabilitiesCurrent`
- ROE = `NetIncomeLoss / StockholdersEquity`
- Share issuance rate = absolute year-over-year growth of `WeightedAverageNumberOfSharesOutstanding`
- EPS growth = year-over-year growth of EPS

Average pass thresholds:

- Net profit margin average >= 20%
- Net income growth average >= 10%
- Debt ratio average < 75%
- Current ratio average >= 100%
- ROE average >= 25%
- Share issuance rate average < 10%
- EPS growth average >= 7.5%

Scoring:

- Average criterion gives `0` or `1`.
- Average plus/minus standard deviation criterion gives `0`, `0.5`, or `1`.
- Final score uses the weighted standard-deviation score, from `0` to `7`.
- Final score >= `3` is suitable; otherwise it is unsuitable.

## ETF Analysis

ETFs are not analyzed as if they were companies. The app analyzes the ETF's top holdings as individual companies using the existing SEC stock analyzer.

ETF score:

- Each successful holding has a company score from `0` to `7`.
- Simple average score uses only successfully analyzed holdings.
- Weighted average score is `sum(company score * holding weight) / sum(successful holding weight)`.
- Failed holdings do not stop ETF analysis; their failure reason appears in the holding table.
- Final ETF verdict uses the weighted average score. Score >= `3` is suitable.

## ETF Holdings Limitation

SEC does not provide a direct ETF holdings API.

Current implementation:

- `SPY`, `QQQ`, and `IVV` use hardcoded sample top-10 holdings in `backend/app/etf_holdings.py`.
- Other ETFs can be analyzed with manual holdings input.
- Manual format: `AAPL:7.5, MSFT:7.2, NVDA:6.8`.
- A future holdings provider can replace `get_etf_holdings(etf_ticker)`.

## SEC API Rate-Limit Protection

The backend is intentionally sequential for SEC analysis:

- Uses `requests.Session()`.
- Sends `User-Agent` on every SEC request.
- Waits at least `0.2` seconds between SEC requests, keeping requests around 5 per second or lower.
- Does not parallelize ETF holding analysis.
- Avoids duplicate companyfacts requests through memory and file cache.

## Cache System

Companyfacts JSON is cached under:

```text
backend/cache/companyfacts/
```

Behavior:

- Cache key is the company CIK, for example `CIK0000320193.json`.
- Cache TTL is 24 hours.
- If valid cache exists, SEC is not called.
- A process-local memory cache prevents duplicate calls inside one ETF analysis.
- Cache metadata is included in API responses as `cache`.
- `app/cache.py` exposes an `invalidate()` method so a refresh/delete option can be added later.

## Data Sources

- US company financials: SEC EDGAR `company_tickers.json` and `companyfacts`
- Stock price and splits: Yahoo Finance through `yfinance`
- Exchange rates: Frankfurter API by default
