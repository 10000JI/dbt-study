-- intermediate 그레인(order_id + order_item_number) 유일성 — 조인으로 행 증식이 없음을 보장.
select order_id, order_item_number, count(*) as n
from {{ ref('int_order_items_enriched') }}
group by order_id, order_item_number
having count(*) > 1
