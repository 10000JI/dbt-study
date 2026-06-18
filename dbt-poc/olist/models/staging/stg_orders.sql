with source as (
    select * from {{ source('olist', 'orders') }}
),
renamed as (
    select
        order_id,
        customer_id,
        order_status,
        try_cast(order_purchase_timestamp as timestamp)      as order_purchase_at,
        try_cast(order_approved_at as timestamp)             as order_approved_at,
        try_cast(order_delivered_carrier_date as timestamp)  as order_delivered_carrier_at,
        try_cast(order_delivered_customer_date as timestamp) as order_delivered_customer_at,
        try_cast(order_estimated_delivery_date as timestamp) as order_estimated_delivery_at,
        try_cast(order_purchase_timestamp as date)           as order_purchase_date
    from source
)
select * from renamed
