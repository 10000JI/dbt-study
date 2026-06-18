-- 복합 PK(order_id + payment_sequential) 유일성 회귀 테스트.
select order_id, payment_sequential, count(*) as n
from {{ ref('stg_payments') }}
group by order_id, payment_sequential
having count(*) > 1
