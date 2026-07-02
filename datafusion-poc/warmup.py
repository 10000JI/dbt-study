from datafusion import SessionContext

ctx = SessionContext()                       # 이론 §5: 진입점
ctx.register_csv("customers", "data/customers.csv")
ctx.register_csv("orders", "data/orders.csv")

print("== (1) SELECT ==")
ctx.sql("select * from orders limit 3").show()

print("== (2) 집계 (상태별) ==")
ctx.sql("select status, count(*) n, sum(amount) total from orders group by status order by status").show()

print("== (3) 조인 (국가별 매출) ==")
ctx.sql("""
  select c.country, sum(o.amount) revenue
  from orders o join customers c on o.customer_id = c.customer_id
  group by c.country order by revenue desc
""").show()

print("== (4) EXPLAIN (이론 §4 파이프라인) ==")
ctx.sql("explain select c.country, sum(o.amount) from orders o join customers c using(customer_id) group by c.country").show()
