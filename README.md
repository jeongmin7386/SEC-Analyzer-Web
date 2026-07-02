# SEC Stock Analyzer Web

SEC EDGAR `companyfacts` API 기반 미국 주식 분석 웹앱입니다. React 프론트엔드와 FastAPI 백엔드로 구성되어 있고, 배포 시에는 FastAPI가 React 빌드 결과를 함께 서빙해 하나의 웹사이트로 실행됩니다.

## 프로젝트 구조

```text
.
├─ backend/
│  ├─ main.py
│  ├─ requirements.txt
│  └─ app/
│     ├─ analyzer.py
│     ├─ market_data.py
│     ├─ sec_client.py
│     └─ split_adjustment.py
├─ frontend/
│  ├─ package.json
│  └─ src/
├─ Dockerfile
└─ render.yaml
```

## 로컬 개발

백엔드:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --port 8000
```

프론트엔드:

```powershell
cd frontend
pnpm install
Copy-Item .env.example .env
pnpm dev
```

로컬 개발에서는 `frontend/.env`의 `VITE_API_BASE_URL`을 `http://localhost:8000`으로 둡니다.

## 프로덕션 빌드

```powershell
cd frontend
pnpm install
pnpm build

cd ..\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000
```

`frontend/dist`가 존재하면 FastAPI가 `/`에서 웹사이트를 서빙하고, `/api/*`는 API로 동작합니다. 프로덕션에서는 `VITE_API_BASE_URL`을 비워 같은 도메인의 `/api`를 사용합니다.

## Docker 배포

```powershell
docker build -t sec-stock-analyzer .
docker run --env SEC_USER_AGENT="Your Name your@email.com" -p 8000:8000 sec-stock-analyzer
```

접속 주소:

```text
http://localhost:8000
```

Dockerfile은 다음 순서로 동작합니다.

- Node 단계에서 `frontend` 의존성 설치 및 `pnpm build`
- Python 단계에서 `backend` 의존성 설치
- `frontend/dist`를 Python 이미지로 복사
- FastAPI가 API와 정적 웹사이트를 함께 서빙

## Render 배포

`render.yaml`을 포함했습니다. Render에서 Blueprint로 연결하면 Docker 기반 Web Service로 배포할 수 있습니다.

배포 전에 환경 변수는 실제 값으로 바꿔주세요.

```text
SEC_USER_AGENT=Your Name your@email.com
```

같은 도메인에서 프론트와 백엔드가 함께 제공되므로 `CORS_ORIGINS`는 필요 없습니다. 환율 API는 코드 기본값으로 `https://api.frankfurter.app`를 사용합니다.

## API

- `GET /api/health`
- `GET /api/analysis/{ticker}`
- `GET /api/markets/indices?period=1m`
- `GET /api/markets/stocks/{ticker}/history?period=1y`
- `GET /api/exchange-rates?period=1m`

기간 값은 `1d`, `1w`, `1m`, `1y`, `5y`, `all`을 지원합니다.

## 분석 점수

최근 10년 연간 SEC 데이터 기준으로 다음 항목을 계산합니다.

- 주당 순이익률
- 주식 발행률
- ROE
- 유동 비율
- 부채 비율
- 순이익 성장률
- 당기 순이익률

각 지표는 평균 기준과 표준편차 반영 기준을 분리해서 계산합니다.

- 평균 기준 점수: `mean`이 기준값을 통과하면 1점
- 안정성 점수: positive metric은 `mean - std`, negative metric은 `mean + std`가 기준값을 통과하면 1점
- positive metrics: 당기 순이익률, 순이익 성장률, 유동 비율, ROE, 주당 순이익률
- negative metrics: 부채 비율, 주식 발행률

총점 3점 이상이면 `적합`, 미만이면 `부적합`입니다.

## 보정 로직

Apple Inc.의 정식 SEC 티커는 `AAPL`입니다. 사용자가 흔히 입력하는 `APPL`은 자동으로 `AAPL`로 보정합니다.

SEC `companyfacts`의 연도별 주식 수와 EPS는 액면분할 전후 기준이 섞일 수 있습니다. 백엔드는 yfinance의 split 이력을 사용해 분석 전에 주식 수와 EPS를 최신 기준으로 보정한 뒤 점수 로직을 적용합니다.

## 데이터 소스

- 미국 기업 재무제표: SEC EDGAR `company_tickers.json`, `companyfacts`
- 미국 지수/주가 및 국내 지수: `yfinance` 기반 Yahoo Finance 데이터
- 환율: 기본값은 무료 `Frankfurter` API이며, `.env`의 `EXCHANGE_RATE_BASE_URL`로 교체할 수 있습니다.
