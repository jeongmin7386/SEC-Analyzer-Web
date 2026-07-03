import { formatPercent } from "../formatters.js";

export default function MetricTable({ rows }) {
  if (!rows?.length) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-slate-400">
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">항목</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">평균</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">표준편차(SD)</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">조정값</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">평균 판정</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">안정성 판정</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="text-slate-700">
              <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">
                {row.name}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.mean ?? row.average)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.std ?? row.stdev)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.adjusted_value)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                <PassBadge passed={row.average_pass} />
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                <PassBadge passed={row.stability_pass} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PassBadge({ passed }) {
  return (
    <span className={passClass(passed)}>
      {passed ? "통과" : "미달"}
    </span>
  );
}

function passClass(passed) {
  if (passed) {
    return "inline-flex min-w-14 justify-center rounded-lg bg-emerald-50 px-2 py-1 text-sm font-semibold text-emerald-700";
  }
  return "inline-flex min-w-14 justify-center rounded-lg bg-slate-100 px-2 py-1 text-sm font-semibold text-slate-500";
}
