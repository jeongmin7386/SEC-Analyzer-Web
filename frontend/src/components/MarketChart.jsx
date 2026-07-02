import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber, shortDate } from "../formatters.js";
import { EmptyBlock } from "./common.jsx";

export default function MarketChart({ data, dataKey = "close", color = "#0f172a" }) {
  if (!data?.length) {
    return <EmptyBlock label="그래프 데이터가 없습니다." />;
  }

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <defs>
            <linearGradient id={`fill-${dataKey}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.24} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="date"
            minTickGap={32}
            tick={{ fill: "#64748b", fontSize: 12 }}
            tickFormatter={shortDate}
            tickLine={false}
          />
          <YAxis
            axisLine={false}
            domain={["auto", "auto"]}
            tick={{ fill: "#64748b", fontSize: 12 }}
            tickFormatter={(value) => formatNumber(value, 0)}
            tickLine={false}
            width={64}
          />
          <Tooltip
            formatter={(value) => [formatNumber(value, 2), dataKey === "rate" ? "환율" : "가격"]}
            labelFormatter={(value) => String(value).slice(0, 10)}
            contentStyle={{
              border: "1px solid #e2e8f0",
              borderRadius: 8,
              boxShadow: "0 12px 30px rgba(15, 23, 42, 0.1)",
            }}
          />
          <Area
            dataKey={dataKey}
            fill={`url(#fill-${dataKey})`}
            fillOpacity={1}
            stroke={color}
            strokeWidth={2}
            type="monotone"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

