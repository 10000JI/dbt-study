with orders as (
    select * from {{ ref('stg_orders') }}
),
items as (
    select
        order_id,
        count(*)                    as items_count,
        count(distinct product_id)  as distinct_products,
        sum(item_price)             as gross_item_value,
        sum(freight_value)          as freight_value
    from {{ ref('int_order_items_enriched') }}
    group by order_id
),
payments as (
    select
        order_id,
        sum(payment_value) as payment_value,
        count(*)           as payment_count
    from {{ ref('stg_payments') }}
    group by order_id
)
select
    orders.order_id,
    orders.customer_id,
    orders.order_status,
    orders.order_purchase_at,
    orders.order_purchase_date,
    coalesce(items.items_count, 0)        as items_count,
    coalesce(items.distinct_products, 0)  as distinct_products,
    coalesce(items.gross_item_value, 0)   as gross_item_value,
    coalesce(items.freight_value, 0)      as freight_value,
    coalesce(payments.payment_value, 0)   as payment_value
from orders
left join items    on orders.order_id = items.order_id
left join payments on orders.order_id = payments.order_id
