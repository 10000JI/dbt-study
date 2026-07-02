import time
from datafusion import SessionContext
import duckdb
OLIST = "../dbt-poc/olist/data"
Q = "월별 매출(orders JOIN payments)"

# --- DataFusion ---
ctx = SessionContext()
ctx.register_csv("orders", f"{OLIST}/olist_orders_dataset.csv")
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")
df_sql = """
  select date_trunc('month', cast(o.order_purchase_timestamp as timestamp)) mth,
         sum(p.payment_value) revenue
  from orders o join payments p on o.order_id = p.order_id
  group by 1 order by 1
"""
t = time.perf_counter()
df_res = ctx.sql(df_sql).collect()
df_t = time.perf_counter() - t
df_rows = sum(b.num_rows for b in df_res)

# --- DuckDB (같은 쿼리, 파일 직접 FROM) ---
dd_sql = f"""
  select date_trunc('month', order_purchase_timestamp) mth, sum(payment_value) revenue
  from '{OLIST}/olist_orders_dataset.csv' o
  join '{OLIST}/olist_order_payments_dataset.csv' p using(order_id)
  group by 1 order by 1
"""
t = time.perf_counter()
dd_res = duckdb.sql(dd_sql).fetchall()
dd_t = time.perf_counter() - t

print(f"[DataFusion] {Q}: {df_rows}행, {df_t*1000:.0f}ms")
print(f"[DuckDB]     {Q}: {len(dd_res)}행, {dd_t*1000:.0f}ms")

# 결과 일치 검증 (첫 3개월 매출 대조)
import pyarrow as pa
df_tbl = pa.Table.from_batches(df_res).to_pylist()[:3]
print("\n결과 대조 (첫 3개월):")
print("  DataFusion:", [(str(r['mth'])[:7], round(r['revenue'],2)) for r in df_tbl])
print("  DuckDB    :", [(str(r[0])[:7], round(r[1],2)) for r in dd_res[:3]])
