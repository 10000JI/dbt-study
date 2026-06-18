{{ config(materialized='table') }}
-- SCD2 실습용 소형 변경가능 테이블 (status가 'shipped'인 주문 200건)
select order_id, order_status
from {{ ref('stg_orders') }}
where order_status = 'shipped'
order by order_id
limit 200
