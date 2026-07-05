import { Database, Loader2, Search } from "lucide-react";
import { useState } from "react";
import { apiPost } from "../api.js";
import { formatNumber } from "../formatters.js";
import AnnualTable from "./AnnualTable.jsx";
import { EmptyBlock, ErrorBlock, WarningBlock } from "./common.jsx";
import MarketChart from "./MarketChart.jsx";
import MetricTable from "./MetricTable.jsx";

const sampleEtfs = new Set(["SPY", "QQQ", "IVV"]);

export default function StockAnalysisPage({ title }) {
  const [ticker, setTicker] = useState("AAPL");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;
    if (sampleEtfs.has(symbol)) {
      setResult(null);
      setError(`${symbol} is an ETF. Use the ETF tab instead of stock analysis.`);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const data = await apiPost("/api/analyze/stock", {
        ticker: symbol,
        includePrice: true,
        pricePeriod: "1y",
      });
      setResult(data);
      setTicker(data.ticker || symbol);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-400">Company Facts</p>
          <h2 className="text-2xl font-semibold text-slate-950">{title}</h2>
        </div>
        <form className="panel flex w-full gap-2 p-2 sm:max-w-xl" onSubmit={handleSubmit}>
          <div className="flex flex-1 items-center gap-2 rounded-lg bg-slate-50 px-3">
            <Search className="h-4 w-4 text-slate-400" />
            <input
              className="h-11 w-full bg-transparent text-base font-semibold uppercase text-slate-950 outline-none placeholder:text-slate-400"
              onChange={(event) => setTicker(event.target.value)}
              placeholder="AAPL"
              value={ticker}
            />
          </div>
          <button
            className="inline-flex h-11 min-w-24 items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={loading}
            type="submit"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Analyze
          </button>
        </form>
      </div>

      {error && <ErrorBlock message={error} />}

      {!result && !loading && (
        <EmptyBlock label="Enter one US stock ticker to analyze SEC EDGAR annual companyfacts." />
      )}

      {loading && (
        <div className="panel flex min-h-56 items-center justify-center gap-3 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm font-semibold">Loading SEC analysis</span>
        </div>
      )}

      {result && !loading && (
        <div className="space-y-5">
          <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="panel p-5">
              <p className="text-sm font-medium text-slate-400">{result.ticker}</p>
              <h3 className="mt-1 text-2xl font-semibold text-slate-950">{result.entityName}</h3>
              <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <SummaryTile
                  label="Average score"
                  value={`${formatNumber(result.averageScore ?? result.totalScore, 1)} / 7.0`}
                  tone={result.averageIsSuitable ? "good" : "bad"}
                />
                <SummaryTile
                  label="Weighted score"
                  value={`${formatNumber(result.stabilityScore ?? result.totalScore, 1)} / 7.0`}
                  tone={result.stabilityIsSuitable ?? result.isSuitable ? "good" : "bad"}
                />
                <SummaryTile
                  label="Verdict"
                  value={result.stabilityVerdict || result.verdict}
                  tone={result.stabilityIsSuitable ?? result.isSuitable ? "good" : "bad"}
                />
                <SummaryTile label="CIK" value={result.profile?.cik || "-"} />
              </div>
              <CacheLine cache={result.cache} />
            </div>
            <div className="panel p-5">
              <p className="text-sm font-semibold text-slate-400">Price chart</p>
              <MarketChart color="#059669" data={result.priceHistory} />
            </div>
          </div>

          {result.warnings?.length > 0 && (
            <WarningBlock message={result.warnings.join(" ")} />
          )}

          {result.splitAdjustments?.length > 0 && (
            <WarningBlock
              message={`${result.splitAdjustments.length} annual EPS/share rows were adjusted for stock splits.`}
            />
          )}

          <div className="panel p-4 sm:p-5">
            <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-400">10-year annual data</p>
                <h3 className="text-lg font-semibold text-slate-950">Financial metric scores</h3>
              </div>
              <span className="text-sm font-semibold text-slate-500">
                average {formatNumber(result.averageScore ?? result.totalScore, 1)} / weighted{" "}
                {formatNumber(result.stabilityScore ?? result.totalScore, 1)}
              </span>
            </div>
            <MetricTable rows={result.metricRows} />
          </div>

          <div className="panel p-4 sm:p-5">
            <div className="mb-4">
              <p className="text-sm font-semibold text-slate-400">Annual Facts</p>
              <h3 className="text-lg font-semibold text-slate-950">Annual financial data</h3>
            </div>
            <AnnualTable rows={result.annualRows} />
          </div>
        </div>
      )}
    </section>
  );
}

function CacheLine({ cache }) {
  if (!cache) return null;

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
      <p className="mt-2 text-xl font-semibold">{value}</p>
    </div>
  );
}
