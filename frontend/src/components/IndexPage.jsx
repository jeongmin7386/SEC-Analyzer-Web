import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "../api.js";
import { formatNumber } from "../formatters.js";
import { ChangeText, ErrorBlock, LoadingBlock, PeriodSelector, marketMovementColor } from "./common.jsx";
import MarketChart from "./MarketChart.jsx";

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function hasNasdaqHistory(payload) {
  return Boolean(payload?.items?.find((item) => item.key === "nasdaq" && item.history?.length));
}

async function loadIndicesWithRetry(period) {
  try {
    const data = await apiGet(`/api/markets/indices?period=${period}`);
    if (hasNasdaqHistory(data)) {
      return data;
    }
  } catch {
    await delay(900);
    return apiGet(`/api/markets/indices?period=${period}`);
  }

  await delay(900);
  return apiGet(`/api/markets/indices?period=${period}`);
}

export default function IndexPage() {
  const [period, setPeriod] = useState("1m");
  const [payload, setPayload] = useState(null);
  const [selectedKey, setSelectedKey] = useState("nasdaq");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await loadIndicesWithRetry(period);
        if (cancelled) return;
        setPayload(data);

        const selectedHasHistory = data.items.find(
          (item) => item.key === selectedKey && item.history.length,
        );
        if (!selectedHasHistory) {
          setSelectedKey(data.items.find((item) => item.history.length)?.key || "nasdaq");
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [period]);

  const selected = useMemo(
    () => payload?.items.find((item) => item.key === selectedKey),
    [payload, selectedKey],
  );

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-400">Market Index</p>
          <h2 className="text-2xl font-semibold text-slate-950">지수</h2>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {error && <ErrorBlock message={error} />}
      {loading && !payload ? (
        <LoadingBlock label="지수 데이터를 불러오는 중" />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            {payload?.items.map((item) => (
              <button
                className={`panel min-h-32 p-4 text-left transition hover:-translate-y-0.5 ${
                  selectedKey === item.key ? "border-slate-950" : ""
                }`}
                key={item.key}
                onClick={() => setSelectedKey(item.key)}
                type="button"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-slate-500">{item.name}</p>
                    <p className="mt-1 text-xs text-slate-400">{item.symbol}</p>
                  </div>
                  {loading && <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />}
                </div>
                <p className="mt-5 text-2xl font-semibold text-slate-950">
                  {formatNumber(item.current, 2)}
                </p>
                {item.error ? (
                  <p className="mt-2 line-clamp-2 text-xs font-medium text-rose-600">{item.error}</p>
                ) : (
                  <div className="mt-2">
                    <ChangeText change={item.change} changePercent={item.changePercent} />
                  </div>
                )}
              </button>
            ))}
          </div>

          <div className="panel p-4 sm:p-5">
            <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-slate-400">{selected?.symbol}</p>
                <h3 className="text-lg font-semibold text-slate-950">{selected?.name || "지수 그래프"}</h3>
              </div>
              {selected && <ChangeText change={selected.change} changePercent={selected.changePercent} />}
            </div>
            <MarketChart color={marketMovementColor(selected?.change)} data={selected?.history || []} />
          </div>
        </>
      )}
    </section>
  );
}
