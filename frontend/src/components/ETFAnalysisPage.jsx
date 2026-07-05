import { CheckCircle2, Database, Layers, Loader2, Search, XCircle } from "lucide-react";
import { useState } from "react";
import { apiPost } from "../api.js";
import { formatNumber, formatPercent } from "../formatters.js";
import { EmptyBlock, ErrorBlock, WarningBlock } from "./common.jsx";

const manualPlaceholder = "AAPL:7.5, MSFT:7.2, NVDA:6.8";

export default function ETFAnalysisPage() {
  const [ticker, setTicker] = useState("QQQ");
  const [manualHoldings, setManualHoldings] = useState("");
  const [manualMode, setManualMode] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;

    setLoading(true);
    setError("");
    try {
      const data = await apiPost("/api/analyze/etf", {
        ticker: symbol,
        manualHoldings: manualHoldings.trim() || null,
      });
      setResult(data);
      setTicker(data.etfTicker || symbol);
      setManualMode(data.holdingsSource === "manual");
    } catch (err) {
      setError(err.message);
      if (err.detail?.manualInputRequired) {
        setManualMode(true);
      }
    } finally {
      setLoading(false);
    }
  }

  const summary = result?.summary;

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-400">ETF Holdings</p>
          <h2 className="text-2xl font-semibold text-slate-950">ETF Analysis</h2>
        </div>
        <form className="panel grid w-full gap-3 p-3 sm:max-w-2xl" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg bg-slate-50 px-3">
              <Search className="h-4 w-4 text-slate-400" />
              <input
                className="h-11 w-full bg-transparent text-base font-semibold uppercase text-slate-950 outline-none placeholder:text-slate-400"
                onChange={(event) => setTicker(event.target.value)}
                placeholder="QQQ"
                value={ticker}
              />
            </div>
            <button
              className="inline-flex h-11 min-w-28 items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={loading}
              type="submit"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Analyze
            </button>
          </div>
          {manualMode && (
            <textarea
              className="min-h-20 w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-400"
              onChange={(event) => setManualHoldings(event.target.value)}
              placeholder={manualPlaceholder}
              value={manualHoldings}
            />
          )}
          <button
            className="w-fit rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:text-slate-950"
            onClick={() => setManualMode((value) => !value)}
            type="button"
          >
            {manualMode ? "Hide manual holdings" : "Enter holdings manually"}
          </button>
        </form>
      </div>

      {error && <ErrorBlock message={error} />}

      {!result && !loading && (
        <EmptyBlock label="SPY, QQQ, and IVV use sample top holdings. Other ETFs can use manual holdings." />
      )}

      {loading && (
        <div className="panel flex min-h-56 items-center justify-center gap-3 text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm font-semibold">Analyzing ETF holdings sequentially</span>
        </div>
      )}

      {result && !loading && (
        <div className="space-y-5">
          {result.holdingsSource === "manual" && (
            <WarningBlock message="Manual holdings were used for this ETF analysis." />
          )}

          <div className="panel p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">{result.etfTicker}</p>
                <h3 className="mt-1 text-2xl font-semibold text-slate-950">ETF final summary</h3>
              </div>
              <VerdictBadge suitable={result.isSuitable} verdict={result.verdict} />
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <SummaryTile label="Successful holdings" value={summary?.successfulCount ?? 0} />
              <SummaryTile label="Cache hits" value={summary?.cacheHitCount ?? 0} />
              <SummaryTile
                label="Simple average"
                value={`${formatNumber(summary?.simpleAverageScore, 1)} / 7.0`}
              />
              <SummaryTile
                label="Weighted average"
                value={`${formatNumber(summary?.weightedAverageScore, 1)} / 7.0`}
                tone={result.isSuitable ? "good" : "bad"}
              />
              <SummaryTile label="Final verdict" value={summary?.verdict || result.verdict} tone={result.isSuitable ? "good" : "bad"} />
            </div>
          </div>

          <div className="panel p-4 sm:p-5">
            <div className="mb-4 flex items-center gap-2">
              <Layers className="h-5 w-5 text-slate-500" />
              <h3 className="text-lg font-semibold text-slate-950">ETF holding analysis summary</h3>
            </div>
            <HoldingTable rows={result.holdingRows} />
          </div>
        </div>
      )}
    </section>
  );
}

function HoldingTable({ rows }) {
  if (!rows?.length) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-slate-400">
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">ETF</th>
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">Holding</th>
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">Company</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">Weight</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">Score</th>
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">Verdict</th>
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">Success</th>
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">Cache</th>
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">Failure reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.etfTicker}-${row.ticker}`} className="text-slate-700">
              <td className="whitespace-nowrap border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">
                {row.etfTicker}
              </td>
              <td className="whitespace-nowrap border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">
                {row.ticker}
              </td>
              <td className="min-w-48 border-b border-slate-100 px-3 py-3">{row.name}</td>
              <td className="whitespace-nowrap border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.weight)}
              </td>
              <td className="whitespace-nowrap border-b border-slate-100 px-3 py-3 text-right">
                {row.companyScore === null ? "-" : `${formatNumber(row.companyScore, 1)} / 7.0`}
              </td>
              <td className="whitespace-nowrap border-b border-slate-100 px-3 py-3">
                {row.companyVerdict || "-"}
              </td>
              <td className="whitespace-nowrap border-b border-slate-100 px-3 py-3">
                <StatusBadge success={row.analysisSuccess} />
              </td>
              <td className="whitespace-nowrap border-b border-slate-100 px-3 py-3">
                <CacheBadge cache={row.cache} />
              </td>
              <td className="min-w-64 border-b border-slate-100 px-3 py-3 text-slate-500">
                {row.failureReason || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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

function VerdictBadge({ suitable, verdict }) {
  const className = suitable
    ? "bg-emerald-50 text-emerald-700"
    : "bg-rose-50 text-rose-700";
  const Icon = suitable ? CheckCircle2 : XCircle;

  return (
    <span className={`inline-flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold ${className}`}>
      <Icon className="h-4 w-4" />
      {verdict}
    </span>
  );
}

function StatusBadge({ success }) {
  const className = success
    ? "bg-emerald-50 text-emerald-700"
    : "bg-slate-100 text-slate-500";
  const Icon = success ? CheckCircle2 : XCircle;

  return (
    <span className={`inline-flex min-w-16 items-center justify-center gap-1 rounded-lg px-2 py-1 text-sm font-semibold ${className}`}>
      <Icon className="h-4 w-4" />
      {success ? "OK" : "Fail"}
    </span>
  );
}

function CacheBadge({ cache }) {
  if (!cache) return <span>-</span>;

  return (
    <span className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
      <Database className="h-3.5 w-3.5" />
      {cache.used ? "used" : "new"}:{cache.source || "unknown"}
    </span>
  );
}
