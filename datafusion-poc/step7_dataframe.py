from datafusion import SessionContext, col
from datafusion import functions as f
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")

print("== SQL ==")
ctx.sql("""
  select payment_type, count(*) n, round(avg(payment_value),2) avg_val, round(sum(payment_value),2) total
  from payments group by payment_type order by total desc
""").show()

print("== DataFrame API (메서드 체이닝, 같은 결과) ==")
(ctx.table("payments")
    .aggregate([col("payment_type")],
               [f.count(col("payment_value")).alias("n"),
                f.avg(col("payment_value")).alias("avg_val"),
                f.sum(col("payment_value")).alias("total")])
    .sort(col("total").sort(ascending=False))
    .show())
