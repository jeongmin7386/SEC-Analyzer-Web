import { formatNumber, formatPercent } from "../formatters.js";

export default function AnnualTable({ rows }) {
  if (!rows?.length) {
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-0 text-left text-xs">
        <thead>
          <tr className="text-slate-400">
            <th className="border-b border-slate-200 px-3 py-3 font-semibold">연도</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">매출</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">순이익</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">ROE</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">EPS 성장</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.fiscal_year} className="text-slate-700">
              <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">
                {row.fiscal_year}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatNumber(row.Revenue, 0)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatNumber(row.NetIncomeLoss, 0)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.roe)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatPercent(row.eps_growth)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

