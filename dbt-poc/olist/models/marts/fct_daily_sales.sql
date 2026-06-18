select
    order_purchase_date,
    count(*)                   as orders_count,
    count(distinct customer_id) as distinct_customers,
    sum(gross_item_value)      as gross_item_value,
    sum(freight_value)         as freight_value,
    sum(payment_value)         as payment_value
from {{ ref('fct_orders') }}
where order_purchase_date is not null
group by order_purchase_date
