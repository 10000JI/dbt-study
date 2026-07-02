# DataFusion 2차 (본편) — 실습 가이드

> 위치: `datafusion-poc/` · 선행: `START_1차.md`(워밍업 완료) · 짝: dbt의 2차(Olist)와 같은 역할
> **목표**: **Olist 실데이터**(dbt 2차와 동일 데이터)로 DataFusion을 본격 사용 — external table·**CSV→Parquet**·DataFrame API 심화·**UDF**·**DuckDB 병행 비교**.
> **데이터**: `../dbt-poc/olist/data/olist_*_dataset.csv` (이미 받아둔 것 재사용, 복사 X)

---

## 0. 1차 → 2차 무엇이 달라지나

| | 1차 (워밍업) | 2차 (본편) |
|---|---|---|
| 데이터 | 6행 샘플 | **Olist 99k+ 주문 실데이터** |
| 포맷 | CSV | CSV **+ Parquet 변환·비교** |
| API | SQL·DataFrame 맛보기 | **DataFrame API 심화** |
| 확장 | — | **UDF(사용자 정의 함수)** |
| 비교 | — | **DuckDB 병행 비교** |

**2차에서 검증할 이론**:
- §3.1(6)·§6 **Parquet 1급 지원** — CSV→Parquet 변환 후 계획·크기·속도 차이
- §3.2 **확장성** — UDF 등록해서 SQL에서 호출
- §3.3 대용량에서 **파티션 병렬**이 실제 이득(1차 6행에선 오버킬이었음)
- §9.1 **vs DuckDB** — 같은 쿼리, 두 엔진 결과·사용감

---

## 1. 환경 추가
1차 venv 재사용 + DuckDB만 추가(병행 비교용).
```bash
cd "/Users/n-mjkim/workspace2/dbt, datafusion/datafusion-poc"
uv pip install --python .venv/bin/python duckdb
.venv/bin/python -c "import datafusion, duckdb; print('df', datafusion.__version__, '/ duckdb', duckdb.__version__)"
```

---

## 2. STEP 5 · Olist external table (실데이터)

`step5_olist.py`:
```python
from datafusion import SessionContext
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("orders",   f"{OLIST}/olist_orders_dataset.csv")
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")

print("== 행수 ==")
ctx.sql("select count(*) as orders from orders").show()

print("== 상태별 주문 ==")
ctx.sql("select order_status, count(*) n from orders group by order_status order by n desc").show()

print("== 월별 매출 (조인+집계) ==")
ctx.sql("""
  select date_trunc('month', cast(o.order_purchase_timestamp as timestamp)) as month,
         sum(p.payment_value) as revenue
  from orders o join payments p on o.order_id = p.order_id
  group by 1 order by 1
  limit 12
""").show()

print("== EXPLAIN (대용량에서 파티션 병렬) ==")
ctx.sql("""
  explain select o.order_status, sum(p.payment_value)
  from orders o join payments p on o.order_id = p.order_id
  group by o.order_status
""").show()
```
**관찰**: 99k 주문에서 RepartitionExec 8파티션 병렬이 이제 "오버킬"이 아니라 실제 일함. DataSourceExec가 csv 파일을 스캔.

---

## 3. STEP 6 · CSV → Parquet 변환 + 비교 (이론 §3.1·§6)

`step6_parquet.py`:
```python
from datafusion import SessionContext
import os
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("orders", f"{OLIST}/olist_orders_dataset.csv")

# CSV → Parquet 쓰기 (DataFusion이 Arrow로 읽어 Parquet으로 저장)
os.makedirs("warehouse", exist_ok=True)
ctx.sql("select * from orders").write_parquet("warehouse/orders.parquet")

# 파일 크기 비교
csv_mb = os.path.getsize(f"{OLIST}/olist_orders_dataset.csv")/1e6
# write_parquet은 디렉터리를 만들 수 있음 → 경로 확인
import glob
pq = glob.glob("warehouse/orders.parquet/**/*.parquet", recursive=True) or glob.glob("warehouse/orders.parquet*")
pq_mb = sum(os.path.getsize(p) for p in pq)/1e6
print(f"CSV {csv_mb:.1f}MB  ->  Parquet {pq_mb:.1f}MB (압축)")

# Parquet 등록 후 같은 쿼리 EXPLAIN — parquet 소스 노드/통계 확인
ctx.register_parquet("orders_pq", "warehouse/orders.parquet")
print("== EXPLAIN (parquet) ==")
ctx.sql("explain select order_status, count(*) from orders_pq group by order_status").show()
```
**관찰**: ① Parquet이 CSV보다 **작음**(압축·컬럼형) ② EXPLAIN의 DataSourceExec가 `file_type=parquet` ③ 이론 §3.1(6) "Parquet 저장→Arrow 연산" 패턴.
> CLI로도: `COPY (SELECT * FROM orders) TO 'warehouse/orders.parquet' STORED AS PARQUET;`

---

## 4. STEP 7 · DataFrame API 심화 (sql vs 메서드 체이닝)

`step7_dataframe.py`:
```python
from datafusion import SessionContext, col
from datafusion import functions as f
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")

# 같은 질의를 두 방식으로: 결제수단별 평균/합, 큰 순
print("== SQL ==")
ctx.sql("""
  select payment_type, count(*) n, round(avg(payment_value),2) avg_val, sum(payment_value) total
  from payments group by payment_type order by total desc
""").show()

print("== DataFrame API (메서드 체이닝) ==")
(ctx.table("payments")
    .aggregate([col("payment_type")],
               [f.count(col("payment_value")).alias("n"),
                f.avg(col("payment_value")).alias("avg_val"),
                f.sum(col("payment_value")).alias("total")])
    .sort(col("total").sort(ascending=False))
    .show())
```
**관찰**: 두 방식이 같은 결과. DataFrame API는 filter/aggregate/sort/limit를 **메서드로 조립**(이론 §1). `.collect()`는 `Vec<RecordBatch>`(Python은 list of RecordBatch) 반환, `.show()`는 출력.

---

## 5. STEP 8 · UDF (사용자 정의 함수 — 이론 §3.2 확장성)

`step8_udf.py`:
```python
from datafusion import SessionContext, udf, col
import pyarrow as pa
import pyarrow.compute as pc
OLIST = "../dbt-poc/olist/data"
ctx = SessionContext()
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")

# 스칼라 UDF: 결제액을 구간(bucket)으로 분류
def bucket(amount: pa.Array) -> pa.Array:
    # pyarrow compute로 벡터 연산 (Arrow 네이티브)
    hi = pc.if_else(pc.greater(amount, 200.0), pa.scalar("high"), pa.scalar("mid"))
    return pc.if_else(pc.less(amount, 50.0), pa.scalar("low"), hi)

bucket_udf = udf(bucket, [pa.float64()], pa.string(), "immutable", name="pay_bucket")
ctx.register_udf(bucket_udf)

print("== UDF로 구간별 집계 ==")
ctx.sql("""
  select pay_bucket(payment_value) as bucket, count(*) n
  from payments group by 1 order by n desc
""").show()
```
**관찰**: 직접 만든 `pay_bucket()`을 SQL에서 일반 함수처럼 호출 → 이론 §3.2 "스칼라 UDF로 확장" 실증. (API 세부는 datafusion 54 기준, 실행 시 조정 가능.)

---

## 6. STEP 9 · DuckDB 병행 비교 (이론 §9.1)

`step9_compare.py`:
```python
import time
from datafusion import SessionContext
import duckdb
OLIST = "../dbt-poc/olist/data"
Q_DESC = "월별 매출(orders⨝payments)"

# --- DataFusion ---
ctx = SessionContext()
ctx.register_csv("orders", f"{OLIST}/olist_orders_dataset.csv")
ctx.register_csv("payments", f"{OLIST}/olist_order_payments_dataset.csv")
df_sql = """
  select date_trunc('month', cast(o.order_purchase_timestamp as timestamp)) month,
         sum(p.payment_value) revenue
  from orders o join payments p on o.order_id = p.order_id
  group by 1 order by 1
"""
t=time.perf_counter(); df_res = ctx.sql(df_sql).collect(); df_t=time.perf_counter()-t
print(f"[DataFusion] {Q_DESC}: {sum(b.num_rows for b in df_res)}행, {df_t*1000:.0f}ms")

# --- DuckDB (같은 쿼리) ---
dd_sql = f"""
  select date_trunc('month', order_purchase_timestamp) month, sum(payment_value) revenue
  from '{OLIST}/olist_orders_dataset.csv' o
  join '{OLIST}/olist_order_payments_dataset.csv' p using(order_id)
  group by 1 order by 1
"""
t=time.perf_counter(); dd_res = duckdb.sql(dd_sql).fetchall(); dd_t=time.perf_counter()-t
print(f"[DuckDB]     {Q_DESC}: {len(dd_res)}행, {dd_t*1000:.0f}ms")
```
**비교 축**: ① **결과 일치**(행수·매출값) ② **API 사용감**(DataFusion=register 후 sql / DuckDB=파일 직접 FROM) ③ **속도**(첫 실행은 준비비용 포함, 참고용) ④ SQL 방언 차이(`date_trunc` 등).
> 핵심: "같은 질문에 두 엔진이 같은 답 + 쓰는 느낌 차이" — 발표의 "두 도구 비교" 파트.

---

## 7. 2차 완료 기준
- [ ] Olist CSV external table 등록 + 집계/조인 쿼리
- [ ] CSV→Parquet 변환 + 크기·계획 비교
- [ ] DataFrame API 심화(sql과 동일 결과)
- [ ] UDF 1개 등록·SQL에서 호출
- [ ] DuckDB 병행 비교(결과 일치 + 사용감/속도 메모)
- [ ] `실습로그.md`에 STEP 5~9 기록
→ 끝나면 **DataFusion 학습 완료** → 발표 자료(dbt·DataFusion 정리)로 마무리.
