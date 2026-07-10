import { formatMoney, formatPercent } from "../formatters.js";

export default function AnnualTable({ rows, currency = "USD" }) {
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
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">영업이익</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">순이익</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">자산</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">부채</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">ROE</th>
            <th className="border-b border-slate-200 px-3 py-3 text-right font-semibold">EPS 성장률</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.fiscalYear || row.fiscal_year} className="text-slate-700">
              <td className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950">
                {row.fiscalYear || row.fiscal_year}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatMoney(row.revenue ?? row.Revenue, currency)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatMoney(row.operatingIncome, currency)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatMoney(row.netIncome ?? row.NetIncomeLoss, currency)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatMoney(row.totalAssets ?? row.Assets, currency)}
              </td>
              <td className="border-b border-slate-100 px-3 py-3 text-right">
                {formatMoney(row.totalLiabilities ?? row.Liabilities, currency)}
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
