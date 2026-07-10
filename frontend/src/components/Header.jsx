import { BarChart3, CircleDollarSign, Search } from "lucide-react";

const items = [
  { key: "stocks", label: "주식 분석", icon: Search },
  { key: "indices", label: "지수", icon: BarChart3 },
  { key: "fx", label: "환율", icon: CircleDollarSign },
];

export default function Header({ active, onChange }) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/86 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-400">Global Stock Analyzer</p>
          <h1 className="text-xl font-semibold text-slate-950">KR·US Stock Analyzer</h1>
        </div>
        <nav className="flex flex-wrap gap-2">
          {items.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.key;
            return (
              <button
                key={item.key}
                className={`nav-button ${isActive ? "nav-button-active" : ""}`}
                onClick={() => onChange(item.key)}
                type="button"
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
