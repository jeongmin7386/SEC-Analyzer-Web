import { useState } from "react";
import ExchangePage from "./components/ExchangePage.jsx";
import Header from "./components/Header.jsx";
import IndexPage from "./components/IndexPage.jsx";
import StockAnalysisPage from "./components/StockAnalysisPage.jsx";

export default function App() {
  const [active, setActive] = useState("stocks");

  return (
    <div className="min-h-screen text-slate-950">
      <Header active={active} onChange={setActive} />
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {active === "stocks" && <StockAnalysisPage />}
        {active === "indices" && <IndexPage />}
        {active === "fx" && <ExchangePage />}
      </main>
    </div>
  );
}
