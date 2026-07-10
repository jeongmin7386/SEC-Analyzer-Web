import { formatNumber, formatPercent } from "../formatters.js";

export default function MetricTable({ rows }) {
  if (!rows?.length) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-slate-400">
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">지표</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">평균</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">표준편차</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">기준</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">상태</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">점수</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="text-slate-700">
              <td className="border-b border-slate-100 px-3 py-3">
                <div className="font-semibold text-slate-950">{row.name}</div>
                {row.note && <div className="mt-1 text-xs text-slate-400">{row.note}</div>}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.mean ?? row.average)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.std ?? row.stdev)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {row.threshold}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                <StatusBadge status={row.status || row.judgement} passed={row.average_pass} />
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right font-semibold">
                {formatNumber(row.score, 1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status, passed }) {
  const normalized = status || (passed ? "PASS" : "FAIL");
  if (normalized === "PASS") {
    return <span className="inline-flex min-w-20 justify-center rounded-lg bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">PASS</span>;
  }
  if (normalized === "INSUFFICIENT_DATA") {
    return <span className="inline-flex min-w-20 justify-center rounded-lg bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">데이터 부족</span>;
  }
  return <span className="inline-flex min-w-20 justify-center rounded-lg bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700">FAIL</span>;
}
