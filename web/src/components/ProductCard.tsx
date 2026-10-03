import type { components } from "../api/schema";
import { amountParts, lastFour } from "../format";
import { useMessages } from "../i18n/messages";
import { productLabels } from "../products";

type ProductCardProps = {
  product: components["schemas"]["Product"];
};

export function ProductCard({ product }: ProductCardProps) {
  const labels = productLabels(product, useMessages().products);
  const ending = lastFour(product.product_number);
  const { whole, cents } = amountParts(product.current_balance);
  return (
    <article className="product solid">
      <div className="product-top">
        <h2 className="label">{labels.name}</h2>
        <span className="muted">
          <span aria-hidden="true">••••{ending}</span>
          <span className="sr-only">
            {labels.maskedEnding} {ending}
          </span>
        </span>
      </div>
      <p className="amount">
        {whole}
        <small>
          .{cents} {product.currency}
        </small>
      </p>
      <p className="caption muted">{labels.status}</p>
    </article>
  );
}
