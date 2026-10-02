import { useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { AppBar } from "../components/AppBar";
import { ErrorCard } from "../components/ErrorCard";
import { ProductCard } from "../components/ProductCard";
import { ProductRows } from "../components/ProductRows";
import { LOGIN_PATH } from "../routes";
import { signOut } from "../session/session";

const PLACEHOLDER_CARDS = 2;

async function loadHome() {
  const [me, products] = await Promise.all([api.GET("/me"), api.GET("/products")]);
  if (me.data === undefined || products.data === undefined) {
    return {};
  }
  return { data: { customer: me.data, products: products.data.products } };
}

export function Home() {
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(0);
  const home = useLoad(loadHome, attempt);

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
            <span className="sr-only">Cargando</span>
            <span className="pulse greeting" />
            <div className="products">
              {Array.from({ length: PLACEHOLDER_CARDS }, (_, index) => (
                <span key={index} className="pulse product-slot" />
              ))}
            </div>
          </div>
        )}
        {home.status === "error" && <ErrorCard message="No pudimos cargar tus productos." onRetry={() => setAttempt((n) => n + 1)} />}
        {home.status === "ready" && (
          <div className="enter">
            <div className="intro">
              <h1 className="display">Hola, {home.data.customer.first_name}</h1>
              {home.data.products.length === 0 && <p className="lede">Todavía no tienes productos con nosotros.</p>}
            </div>
            {home.data.products.length > 0 && (
              <div className="products">
                {home.data.products.map((product) => (
                  <ProductCard key={product.product_id} product={product} />
                ))}
              </div>
            )}
            <ProductRows />
          </div>
        )}
      </main>
    </>
  );
}
