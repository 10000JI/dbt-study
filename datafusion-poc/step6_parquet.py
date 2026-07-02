from datafusion import SessionContext
import os, glob
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("orders", f"{OLIST}/olist_orders_dataset.csv")

os.makedirs("warehouse", exist_ok=True)
# CSV → Parquet (DataFusion이 Arrow로 읽어 Parquet으로 저장)
ctx.sql("select * from orders").write_parquet("warehouse/orders.parquet")

# 크기 비교
csv_mb = os.path.getsize(f"{OLIST}/olist_orders_dataset.csv")/1e6
target = "warehouse/orders.parquet"
if os.path.isdir(target):
    pq = glob.glob(f"{target}/**/*.parquet", recursive=True)
else:
    pq = [target]
pq_mb = sum(os.path.getsize(p) for p in pq)/1e6
print(f"CSV {csv_mb:.1f}MB  ->  Parquet {pq_mb:.1f}MB  (압축비 {csv_mb/pq_mb:.1f}x)")
print("parquet 파일:", pq)

# Parquet 등록 후 같은 쿼리 EXPLAIN
ctx.register_parquet("orders_pq", target)
print("== EXPLAIN (parquet 소스) ==")
ctx.sql("explain select order_status, count(*) from orders_pq group by order_status").show()
