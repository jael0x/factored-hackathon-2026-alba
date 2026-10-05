-- PLAN.md D24: a case starts from a product on the home, and a customer may have one open case per product.
-- An older case with no product stays outside the index, since nulls never collide.
DROP INDEX processes_one_open_per_customer_idx;

CREATE UNIQUE INDEX processes_one_open_per_product_idx
    ON processes (customer_id, process_key, product)
    WHERE state <> 'ended';
