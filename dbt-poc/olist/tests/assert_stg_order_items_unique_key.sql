-- 복합 PK(order_id + order_item_number) 유일성 회귀 테스트. 중복 그레인 행이 있으면 실패.
select order_id, order_item_number, count(*) as n
from {{ ref('stg_order_items') }}
group by order_id, order_item_number
having count(*) > 1
