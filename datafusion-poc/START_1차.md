# DataFusion 1차 (워밍업) — 실습 가이드

> 위치: `datafusion-poc/` · 선행: `Apache DataFusion (이론).md` · 짝: dbt의 1차(jaffle)와 같은 역할
> **목표**: "제공된 작은 샘플 데이터"로 DataFusion **기본 동작을 1차로 빠르게 체감**한다. (실데이터 Olist·Parquet·UDF·DuckDB 비교는 **2차**)
> **경로**: Rust 미경험 → **CLI + Python**으로만 진행.

---

## 0. 1차 vs 2차 (dbt와 같은 구도)

| | 1차 (워밍업·제공된 것) | 2차 (본편·실데이터 직접) |
|---|---|---|
| dbt | jaffle 클론 → `dbt build` 돌려봄 | Olist로 seed·stg·마트 직접 |
| **DataFusion (이 문서=1차)** | **작은 샘플 CSV로 CLI/Python 기본 동작·EXPLAIN 체감** | Olist external table·CSV→Parquet·DataFrame API·UDF·DuckDB 비교 |

**1차에서 검증할 이론(노트 대조)**:
- §5 `SessionContext`가 진입점(등록·SQL·DataFrame 시작점)인지
- §4 쿼리 실행 파이프라인(SQL→LogicalPlan→최적화→물리계획→실행)이 `EXPLAIN`에서 보이는지
- §3.1 결과가 **Arrow RecordBatch**(컬럼형)로 나오는지
- §1 SQL과 DataFrame **두 API**가 같은 결과를 내는지(맛보기)

---

## 1. 환경 셋업

### 1.1 Python 패키지 (필수)
```bash
cd "/Users/n-mjkim/workspace2/dbt, datafusion/datafusion-poc"
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python datafusion
.venv/bin/python -c "import datafusion; print('datafusion', datafusion.__version__)"
```
기대: `datafusion <버전>` 출력.

### 1.2 datafusion-cli (가능하면)
```bash
brew install datafusion      # Homebrew 포뮬러로 datafusion-cli 제공 시도
datafusion-cli --version
```
- 설치 안 되면 **1차는 Python만으로 진행**해도 충분(CLI는 2차에서 다시 시도). CLI/Python은 같은 엔진이라 학습 손실 없음.

### 1.3 샘플 데이터 생성 (제공된 것 역할 — 작게)
`data/customers.csv`, `data/orders.csv` 2개 작은 CSV를 만든다(조인 연습용).
```
# data/customers.csv
customer_id,name,country
1,Alice,KR
2,Bob,US
3,Carol,KR
4,Dave,JP

# data/orders.csv
order_id,customer_id,amount,status
1001,1,120.0,completed
1002,1,80.0,completed
1003,2,200.0,shipped
1004,3,50.0,completed
1005,3,75.0,returned
1006,4,300.0,shipped
```

---

## 2. CLI 워밍업 (datafusion-cli 설치된 경우)

`datafusion-cli` 실행 후 한 줄씩:

```sql
-- (1) external table 등록 — CSV를 테이블로 노출
CREATE EXTERNAL TABLE customers STORED AS CSV LOCATION 'data/customers.csv' OPTIONS ('has_header' 'true');
CREATE EXTERNAL TABLE orders    STORED AS CSV LOCATION 'data/orders.csv'    OPTIONS ('has_header' 'true');

-- (2) SELECT
SELECT * FROM orders LIMIT 3;

-- (3) 집계
SELECT status, count(*) AS n, sum(amount) AS total FROM orders GROUP BY status;

-- (4) 조인 (국가별 매출)
SELECT c.country, sum(o.amount) AS revenue
FROM orders o JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.country ORDER BY revenue DESC;

-- (5) 실행계획 관찰 (이론 §4)
EXPLAIN SELECT c.country, sum(o.amount) FROM orders o JOIN customers c USING(customer_id) GROUP BY c.country;
```
**관찰 포인트**: `EXPLAIN` 출력에 **logical_plan / physical_plan**이 단계로 나뉘어 나오는지, `Aggregate`·`Join`·`TableScan` 같은 연산자와 푸시다운이 보이는지.

---

## 3. Python 워밍업 (필수)

`warmup.py`를 만들어 실행하거나 `-c`로 한 줄씩.

```python
from datafusion import SessionContext

ctx = SessionContext()                       # 이론 §5: 진입점
ctx.register_csv("customers", "data/customers.csv")
ctx.register_csv("orders", "data/orders.csv")

# (1) SQL API
print("== SELECT ==")
ctx.sql("select * from orders limit 3").show()

print("== 집계 ==")
ctx.sql("select status, count(*) n, sum(amount) total from orders group by status").show()

print("== 조인 ==")
ctx.sql("""
  select c.country, sum(o.amount) revenue
  from orders o join customers c on o.customer_id = c.customer_id
  group by c.country order by revenue desc
""").show()

# (2) EXPLAIN — 이론 §4 파이프라인 관찰
print("== EXPLAIN ==")
ctx.sql("explain select c.country, sum(o.amount) from orders o join customers c using(customer_id) group by c.country").show()

# (3) DataFrame API 맛보기 — SQL과 같은 결과인지 (이론 §1, 본격 비교는 2차)
from datafusion import functions as f, col
print("== DataFrame API ==")
df = ctx.table("orders").aggregate([col("status")], [f.sum(col("amount")).alias("total")])
df.show()
```

**관찰 포인트**:
- `SessionContext`에 등록 → `ctx.sql(...).show()`로 바로 결과(이론 §5 검증)
- `.show()` 결과가 표(컬럼형 RecordBatch) 형태인지(이론 §3.1)
- `explain` 출력에 logical/physical plan 단계가 보이는지(이론 §4)
- SQL 집계와 DataFrame 집계 결과가 일치하는지(이론 §1)

---

## 4. 1차 완료 기준 (→ 2차 전환)
- [ ] `datafusion` 설치 + `SessionContext`로 CSV 등록·SELECT 성공
- [ ] 집계·조인 쿼리 동작 확인
- [ ] `EXPLAIN`으로 실행계획(logical/physical) 1회 관찰
- [ ] SQL ↔ DataFrame API 같은 결과 맛보기
- [ ] (선택) datafusion-cli로 동일 흐름
→ 손에 익으면 **2차**: Olist 실데이터 external table·**CSV→Parquet**·DataFrame API 심화·**UDF**·**DuckDB 병행 비교**.

## 5. 실습 로그
실행한 명령/관찰/이론과 다른 점은 `datafusion-poc/실습로그.md`에 기록(dbt와 동일 포맷).
