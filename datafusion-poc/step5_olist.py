from datafusion import SessionContext
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("orders",   f"{OLIST}/olist_orders_dataset.csv")
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")

print("== 행수 ==")
ctx.sql("select count(*) as orders from orders").show()

print("== 상태별 주문 ==")
ctx.sql("select order_status, count(*) n from orders group by order_status order by n desc").show()

print("== 월별 매출 (조인+집계, 최근 12개월) ==")
ctx.sql("""
  select date_trunc('month', cast(o.order_purchase_timestamp as timestamp)) as month,
         sum(p.payment_value) as revenue
  from orders o join payments p on o.order_id = p.order_id
  group by 1 order by 1 desc
  limit 12
""").show()

print("== EXPLAIN (대용량에서 파티션 병렬) ==")
ctx.sql("""
  explain select o.order_status, sum(p.payment_value)
  from orders o join payments p on o.order_id = p.order_id
  group by o.order_status
""").show()
