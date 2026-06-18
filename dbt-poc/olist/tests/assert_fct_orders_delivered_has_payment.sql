{{ config(severity='warn') }}
-- 설계 §6 정합성 검사: 아이템이 있고 배송완료(delivered)인데 결제 기록이 0인 주문.
-- Olist 실데이터엔 이런 결제 누락 주문이 소수 존재(알려진 quirk) → 빌드를 깨지 않도록 warn.
select order_id, items_count, payment_value, order_status
from {{ ref('fct_orders') }}
where items_count > 0
  and payment_value = 0
  and order_status = 'delivered'
