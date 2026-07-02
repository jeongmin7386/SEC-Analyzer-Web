import { AlertCircle, AlertTriangle, Loader2 } from "lucide-react";
import { formatPercent, formatSigned } from "../formatters.js";

export const periods = [
  { key: "1d", label: "1일" },
  { key: "1w", label: "1주" },
  { key: "1m", label: "1개월" },
  { key: "1y", label: "1년" },
  { key: "5y", label: "5년" },
  { key: "all", label: "전체" },
];

export function PeriodSelector({ value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {periods.map((period) => (
        <button
          className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
            value === period.key
              ? "border-slate-950 bg-slate-950 text-white"
              : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-950"
          }`}
          key={period.key}
          onClick={() => onChange(period.key)}
          type="button"
        >
          {period.label}
        </button>
      ))}
    </div>
  );
}

export function LoadingBlock({ label = "불러오는 중" }) {
  return (
    <div className="panel flex min-h-56 items-center justify-center gap-3 text-slate-500">
      <Loader2 className="h-5 w-5 animate-spin" />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}

export function ErrorBlock({ message }) {
  return (
    <div className="panel flex items-start gap-3 border-rose-200 bg-rose-50 p-4 text-rose-700">
      <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}

export function WarningBlock({ message }) {
  return (
    <div className="panel flex items-start gap-3 border-amber-200 bg-amber-50 p-4 text-amber-800">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}

export function EmptyBlock({ label = "표시할 데이터가 없습니다." }) {
  return (
    <div className="muted-panel flex min-h-56 items-center justify-center p-6 text-center text-sm font-medium text-slate-500">
      {label}
    </div>
  );
}

export function ChangeText({ change, changePercent }) {
  const isUp = Number(change) > 0;
  const isDown = Number(change) < 0;
  const color = isUp ? "text-emerald-600" : isDown ? "text-rose-600" : "text-slate-500";

  return (
    <span className={`text-sm font-semibold ${color}`}>
      {formatSigned(change)} · {formatPercent(changePercent)}
    </span>
  );
}
