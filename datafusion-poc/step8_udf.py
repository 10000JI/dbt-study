from datafusion import SessionContext, udf
import pyarrow as pa
import pyarrow.compute as pc
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")

# 스칼라 UDF: 결제액을 구간(bucket)으로 분류 (Arrow 벡터 연산)
def bucket(amount: pa.Array) -> pa.Array:
    hi = pc.if_else(pc.greater(amount, 200.0), "high", "mid")
    return pc.if_else(pc.less(amount, 50.0), "low", hi)

pay_bucket = udf(bucket, [pa.float64()], pa.string(), "immutable", name="pay_bucket")
ctx.register_udf(pay_bucket)

print("== 직접 만든 UDF pay_bucket()을 SQL에서 호출 ==")
ctx.sql("""
  select pay_bucket(payment_value) as bucket,
         count(*) n,
         round(sum(payment_value),2) total
  from payments
  group by 1 order by total desc
""").show()
