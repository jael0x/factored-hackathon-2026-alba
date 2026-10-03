from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.contract_models import Product, ProductList
from api.domain.products.product import CustomerProduct
from api.domain.session.tokens import SessionClaims
from api.presentation.http.dependencies import ListProducts, get_list_products, require_customer

router = APIRouter()


@router.get("/products", response_model=ProductList)
def read_products(
    session: Annotated[SessionClaims, Depends(require_customer)],
    list_products: Annotated[ListProducts, Depends(get_list_products)],
    customer_id: Annotated[str | None, Query(min_length=1)] = None,
) -> ProductList:
    return ProductList(products=[_wire_product(product) for product in list_products(session.sub, customer_id)])


def _wire_product(product: CustomerProduct) -> Product:
    return Product(
        product_id=product.product_id,
        product_type=product.product_type,
        product_number=product.product_number,
        currency=product.currency,
        current_balance=float(product.current_balance),
        product_status=product.product_status,
    )
