with products as (
    select * from {{ ref('stg_products') }}
),
category as (
    select * from {{ ref('product_category_name_translation') }}
)
select
    products.product_id,
    products.product_category_name,
    coalesce(category.product_category_name_english, products.product_category_name) as product_category,
    products.product_weight_g,
    products.product_length_cm,
    products.product_height_cm,
    products.product_width_cm
from products
left join category on products.product_category_name = category.product_category_name
