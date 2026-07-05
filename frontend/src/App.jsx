import { useState } from "react";
import ETFAnalysisPage from "./components/ETFAnalysisPage.jsx";
import ExchangePage from "./components/ExchangePage.jsx";
import Header from "./components/Header.jsx";
import IndexPage from "./components/IndexPage.jsx";
import StockAnalysisPage from "./components/StockAnalysisPage.jsx";

export default function App() {
  const [active, setActive] = useState("indices");

  return (
    <div className="min-h-screen text-slate-950">
      <Header active={active} onChange={setActive} />
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {active === "indices" && <IndexPage />}
        {active === "analysis" && <StockAnalysisPage title="주요 분석" />}
        {active === "stocks" && <StockAnalysisPage title="주식" />}
        {active === "etf" && <ETFAnalysisPage />}
        {active === "fx" && <ExchangePage />}
      </main>
    </div>
  );
}
