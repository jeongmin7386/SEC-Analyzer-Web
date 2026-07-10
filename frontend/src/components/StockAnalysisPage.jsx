import { Database, Loader2, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../api.js";
import { formatMoney, formatNumber } from "../formatters.js";
import AnnualTable from "./AnnualTable.jsx";
import { EmptyBlock, ErrorBlock, WarningBlock } from "./common.jsx";
import MarketChart from "./MarketChart.jsx";
import MetricTable from "./MetricTable.jsx";

const marketOptions = [
  { key: "AUTO", label: "자동 판별" },
  { key: "KR", label: "한국 주식" },
  { key: "US", label: "미국 주식" },
];

export default function StockAnalysisPage() {
  const [marketMode, setMarketMode] = useState("AUTO");
  const [query, setQuery] = useState("AAPL");
  const [searchPayload, setSearchPayload] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [result, setResult] = useState(null);
  const [searching, setSearching] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const value = query.trim();
    setSelectedCandidate(null);
    if (!value) {
      setSearchPayload(null);
      return undefined;
    }

    let cancelled = false;
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await searchStocks(value, marketMode);
        if (!cancelled) setSearchPayload(data);
      } catch {
        if (!cancelled) setSearchPayload(null);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, marketMode]);

  async function handleSubmit(event) {
    event.preventDefault();
    const value = query.trim();
    if (!value || analyzing) return;

    setError("");
    const candidate = selectedCandidate || singleCandidate(searchPayload);
    if (candidate) {
      await analyzeCandidate(candidate);
      return;
    }

    setSearching(true);
    try {
      const data = await searchStocks(value, marketMode);
      setSearchPayload(data);
      const exact = singleCandidate(data);
      if (exact) {
        await analyzeCandidate(exact);
      } else if (data.results?.length) {
        setError("후보가 여러 개입니다. 아래 목록에서 분석할 종목을 선택해 주세요.");
      } else {
        setError("검색 결과가 없습니다.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  }

  async function analyzeCandidate(candidate) {
    setAnalyzing(true);
    setError("");
    try {
      const data = await apiPost("/api/stocks/analyze", {
        market: candidate.market,
        symbol: candidate.symbol,
        presetId: candidate.market === "KR" ? "kr-market" : "default",
        years: 10,
        includePrice: true,
        pricePeriod: "1y",
      });
      setResult(data);
      setQuery(candidate.displaySymbol || candidate.symbol);
      setSelectedCandidate(candidate);
      setSearchPayload({ results: [candidate], ambiguous: false });
    } catch (err) {
      if (err.detail?.candidates?.length) {
        setSearchPayload({ results: err.detail.candidates, ambiguous: true });
        setError(err.detail.message || "후보 목록에서 분석할 종목을 선택해 주세요.");
      } else {
        setError(err.message);
      }
    } finally {
      setAnalyzing(false);
    }
  }

  const candidates = searchPayload?.results || [];
  const company = result?.company || {};
  const currency = result?.currency || company.currency || "USD";
  const latestPrice = result?.priceHistory?.at(-1)?.close;

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-400">KR / US Stocks</p>
          <h2 className="text-2xl font-semibold text-slate-950">주식 분석</h2>
        </div>
        <form className="panel w-full p-3 sm:max-w-3xl" onSubmit={handleSubmit}>
          <div className="mb-3 flex flex-wrap gap-2">
            {marketOptions.map((option) => (
              <button
                className={`rounded-lg border px-3 py-2 text-sm font-semibold transition ${
                  marketMode === option.key
                    ? "border-slate-950 bg-slate-950 text-white"
                    : "border-slate-200 bg-white text-slate-500 hover:border-slate-300"
                }`}
                key={option.key}
                onClick={() => setMarketMode(option.key)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <div className="flex flex-1 items-center gap-2 rounded-lg bg-slate-50 px-3">
              <Search className="h-4 w-4 text-slate-400" />
              <input
                className="h-11 w-full bg-transparent text-base font-semibold text-slate-950 outline-none placeholder:text-slate-400"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="삼성전자, 005930, 005930.KS, AAPL, Apple"
                value={query}
              />
            </div>
            <button
              className="inline-flex h-11 min-w-24 items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={analyzing || searching}
              type="submit"
            >
              {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Analyze
            </button>
          </div>

          {(searching || candidates.length > 0) && (
            <div className="mt-3 rounded-lg border border-slate-100 bg-white">
              {searching && (
                <div className="flex items-center gap-2 px-3 py-3 text-sm font-medium text-slate-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  검색 중
                </div>
              )}
              {!searching && candidates.length > 0 && (
                <div className="divide-y divide-slate-100">
                  {candidates.map((candidate) => (
                    <button
                      className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition hover:bg-slate-50"
                      key={`${candidate.market}-${candidate.symbol}`}
                      onClick={() => analyzeCandidate(candidate)}
                      type="button"
                    >
                      <div>
                        <div className="text-sm font-semibold text-slate-950">
                          {candidate.companyName}
                        </div>
                        <div className="mt-1 text-xs font-medium text-slate-400">
                          {candidate.displaySymbol || candidate.symbol} · {candidate.exchange} · {candidate.market} · {candidate.currency}
                        </div>
                      </div>
                      <span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-500">
                        선택
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </form>
      </div>

      {error && <ErrorBlock message={error} />}

      {!result && !analyzing && (
        <EmptyBlock label="한국 기업명, 한국 종목코드, 미국 티커 또는 미국 기업명을 입력하세요." />
      )}

      {analyzing && (
        <div className="panel flex min-h-56 items-center justify-center gap-3 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm font-semibold">재무 데이터 분석 중</span>
        </div>
      )}

      {result && !analyzing && (
        <div className="space-y-5">
          <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-400">
                    {company.displaySymbol || company.symbol} · {company.exchange} · {currency}
                  </p>
                  <h3 className="mt-1 text-2xl font-semibold text-slate-950">{company.companyName}</h3>
                </div>
                <span className="rounded-lg bg-slate-950 px-3 py-2 text-xs font-semibold text-white">
                  {result.dataSource}
                </span>
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <SummaryTile
                  label="종합 점수"
                  value={`${formatNumber(result.score?.totalScore ?? result.totalScore, 1)} / ${formatNumber(result.score?.maxScore ?? result.maxScore, 1)}`}
                  tone={result.score?.isSuitable ?? result.isSuitable ? "good" : "bad"}
                />
                <SummaryTile
                  label="최종 판정"
                  value={result.score?.verdict || result.verdict}
                  tone={result.score?.isSuitable ?? result.isSuitable ? "good" : "bad"}
                />
                <SummaryTile label="최근 가격" value={formatMoney(latestPrice, currency)} />
                <SummaryTile label={company.market === "KR" ? "corp_code" : "CIK"} value={company.corpCode || company.cik || "-"} />
              </div>
              <p className="mt-4 text-sm font-medium text-slate-500">{result.dataNotice}</p>
              <CacheLine cache={result.cache} />
            </div>
            <div className="panel p-5">
              <p className="text-sm font-semibold text-slate-400">주가 차트</p>
              <MarketChart color="#059669" data={result.priceHistory} />
            </div>
          </div>

          {result.warnings?.length > 0 && <WarningBlock message={result.warnings.join(" ")} />}
          {result.missingFields?.length > 0 && (
            <WarningBlock message={`데이터 부족 항목: ${result.missingFields.join(", ")}`} />
          )}

          <div className="panel p-4 sm:p-5">
            <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-400">Metric Scores</p>
                <h3 className="text-lg font-semibold text-slate-950">지표별 판정</h3>
              </div>
              <span className="text-sm font-semibold text-slate-500">
                {result.score?.presetName || "기본 분석"}
              </span>
            </div>
            <MetricTable rows={result.metrics || result.metricRows} />
          </div>

          <div className="panel p-4 sm:p-5">
            <div className="mb-4">
              <p className="text-sm font-semibold text-slate-400">Annual Financials</p>
              <h3 className="text-lg font-semibold text-slate-950">최근 연도별 재무 추이</h3>
            </div>
            <AnnualTable rows={result.annualRows || result.financials} currency={currency} />
          </div>

          <div className="text-xs font-medium leading-5 text-slate-400">
            이 결과는 투자 판단 참고용이며 투자 조언이 아닙니다. 원본 공시와 데이터 출처를 직접 확인하세요.
          </div>
        </div>
      )}
    </section>
  );
}

async function searchStocks(query, market) {
  return apiGet(`/api/stocks/search?q=${encodeURIComponent(query)}&market=${market}`);
}

function singleCandidate(payload) {
  if (!payload?.results?.length) return null;
  return payload.results.length === 1 ? payload.results[0] : null;
}

function CacheLine({ cache }) {
  if (!cache) return null;

  if (cache.items?.length) {
    const used = cache.items.filter((item) => item.used).length;
    return (
      <div className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-600">
        <Database className="h-4 w-4" />
        <span>Cache: {used}/{cache.items.length} file hits</span>
      </div>
    );
  }

  if (!cache.key && cache.used === undefined) return null;

  return (
    <div className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-600">
      <Database className="h-4 w-4" />
      <span>
        Cache: {cache.used ? "used" : "refreshed"} ({cache.source || "unknown"})
      </span>
    </div>
  );
}

function SummaryTile({ label, value, tone }) {
  const toneClass =
    tone === "good"
      ? "bg-emerald-50 text-emerald-700"
      : tone === "bad"
        ? "bg-rose-50 text-rose-700"
        : "bg-slate-50 text-slate-950";

  return (
    <div className={`rounded-lg border border-slate-200 p-4 ${toneClass}`}>
      <p className="text-xs font-semibold text-slate-400">{label}</p>
      <p className="mt-2 break-words text-xl font-semibold">{value || "-"}</p>
    </div>
  );
}
