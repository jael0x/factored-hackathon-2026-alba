import { useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { AppBar } from "../components/AppBar";
import { ErrorCard } from "../components/ErrorCard";
import { ProductCard } from "../components/ProductCard";
import { ProductRows } from "../components/ProductRows";
import { StartDialog } from "../components/StartDialog";
import type { components } from "../api/schema";
import { newSend } from "../chat";
import { useLocale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { CASE_PATH, LOGIN_PATH, casePath } from "../routes";
import { signOut } from "../session/session";

const PLACEHOLDER_CARDS = 2;

type ProductKey = components["schemas"]["ProductKey"];

async function loadHome() {
  const [me, products, cases] = await Promise.all([api.GET("/me"), api.GET("/products"), api.GET("/cases")]);
  if (me.data === undefined || products.data === undefined || cases.data === undefined) {
    return {};
  }
  return { data: { customer: me.data, products: products.data.products, cases: cases.data.cases } };
}

export function Home() {
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(0);
  const home = useLoad(loadHome, attempt);
  const t = useMessages();
  const locale = useLocale();

  const [starting, setStarting] = useState<ProductKey | null>(null);

  const begin = (key: ProductKey) => {
    setStarting(null);
    navigate(CASE_PATH, { state: { opening: newSend(t.chat.opening[key], locale, key) } });
  };

  const leave = () => {
    signOut();
    navigate(LOGIN_PATH.customer, { replace: true });
  };

  return (
    <>
      <AppBar firstName={home.status === "ready" ? home.data.customer.first_name : undefined} onSignOut={leave} />
      <main className="page">
        {home.status === "loading" && (
          <div role="status">
            <span className="sr-only">{t.loading}</span>
            <span className="pulse greeting" />
            <div className="products">
              {Array.from({ length: PLACEHOLDER_CARDS }, (_, index) => (
                <span key={index} className="pulse product-slot" />
              ))}
            </div>
          </div>
        )}
        {home.status === "error" && <ErrorCard message={t.home.loadFailed} onRetry={() => setAttempt((n) => n + 1)} />}
        {home.status === "ready" && (
          <div className="enter">
            <div className="intro">
              <h1 className="display">{t.home.greeting(home.data.customer.first_name)}</h1>
              {home.data.products.length === 0 && <p className="lede">{t.home.empty}</p>}
            </div>
            {home.data.products.length > 0 && (
              <div className="products">
                {home.data.products.map((product) => (
                  <ProductCard key={product.product_id} product={product} />
                ))}
              </div>
            )}
            <ProductRows cases={home.data.cases} onStart={setStarting} onOpen={(id) => navigate(casePath(id))} />
          </div>
        )}
      </main>
      <StartDialog product={starting} onBegin={begin} onCancel={() => setStarting(null)} />
    </>
  );
}
