-- 실패 = 금액 음수 행이 존재. 0행이면 PASS.
select order_id, gross_item_value, freight_value, payment_value
from {{ ref('fct_orders') }}
where gross_item_value < 0
   or freight_value < 0
   or payment_value < 0
