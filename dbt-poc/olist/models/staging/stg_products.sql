with source as (
    select * from {{ source('olist', 'products') }}
),
renamed as (
    select
        product_id,
        product_category_name,
        cast(product_weight_g as double)  as product_weight_g,
        cast(product_length_cm as double) as product_length_cm,
        cast(product_height_cm as double) as product_height_cm,
        cast(product_width_cm as double)  as product_width_cm
    from source
)
select * from renamed
