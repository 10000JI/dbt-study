with items as (
    select * from {{ ref('stg_order_items') }}
),
products as (
    select * from {{ ref('stg_products') }}
),
category as (
    select * from {{ ref('product_category_name_translation') }}
)
select
    items.order_id,
    items.order_item_number,
    items.product_id,
    items.seller_id,
    products.product_category_name,
    coalesce(category.product_category_name_english, products.product_category_name) as product_category,
    items.item_price,
    items.freight_value,
    items.item_price + items.freight_value as item_total
from items
left join products on items.product_id = products.product_id
left join category on products.product_category_name = category.product_category_name
