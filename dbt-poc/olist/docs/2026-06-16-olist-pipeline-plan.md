# Olist 본편 파이프라인 — 구현 계획 (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Olist 실데이터로 source()→staging→intermediate→marts dbt 파이프라인을 구축하고 tests·snapshots(SCD2)·lineage를 직접 검증한다.

**Architecture:** dbt-duckdb의 external source로 6개 CSV를 raw로 선언 → staging(view, 1:1 정리) → intermediate(조인) → marts(table: fct/dim). 테스트는 generic(arguments 신문법)+singular, SCD2는 통제된 mutable 테이블 변경으로 관찰. 로컬 DuckDB 단일 파일.

**Tech Stack:** dbt-core 1.11 + dbt-duckdb, DuckDB, Python 3.12(uv), 실데이터 Olist(CC BY-NC).

> **dbt에서의 TDD 적응**: 각 모델 태스크는 (1)모델 SQL 작성 → (2)`dbt run`으로 빌드 → (3)스키마 테스트 추가 → (4)`dbt test` → (5)그레인·행수 검증 → (6)커밋 순. "테스트 먼저"는 dbt 특성상 모델 직후 계약(schema.yml) 정의로 대체하되, 검증은 엄격히 한다.

> **작업 디렉터리**: 별도 명시 없으면 모든 명령은 `dbt-poc/olist/`에서 실행. dbt 명령엔 `--profiles-dir .` 사용.

> **커밋 방식**: 워크스페이스 루트는 git 레포가 아니다. Task 0에서 만드는 `commit.sh`가 `dbt-poc/olist/`를 private 레포 `10000JI/dbt-study`로 동기화·푸시한다. 각 "Commit" 스텝은 `bash commit.sh "<message>"` 한 줄.

---

## File Structure

```
dbt-poc/olist/
├── dbt_project.yml              # 프로젝트 설정
├── profiles.yml                 # duckdb 연결 (로컬)
├── .gitignore                   # .venv/ data/ *.duckdb target/ 등 제외
├── README.md                    # 데이터 다운로드 절차 + 실행법
├── commit.sh                    # dbt-study 레포 동기화 헬퍼 (gitignore됨)
├── data/                        # (gitignore) Kaggle CSV 6종
├── seeds/
│   └── product_category_name_translation.csv
├── models/
│   ├── staging/
│   │   ├── _sources.yml         # external source 선언
│   │   ├── stg_orders.sql
│   │   ├── stg_order_items.sql
│   │   ├── stg_products.sql
│   │   ├── stg_payments.sql
│   │   ├── stg_customers.sql
│   │   └── _staging.yml          # staging 테스트
│   ├── intermediate/
│   │   ├── int_order_items_enriched.sql
│   │   └── _intermediate.yml
│   └── marts/
│       ├── dim_customers.sql
│       ├── dim_products.sql
│       ├── fct_orders.sql
│       ├── fct_daily_sales.sql
│       └── _marts.yml            # 마트 테스트
├── tests/
│   └── assert_fct_orders_amounts_non_negative.sql   # singular test
├── snapshots/
│   └── orders_snapshot.yml
└── models/snapshot_src/
    └── snap_orders_src.sql       # SCD2 실습용 mutable 테이블
```

---

## Task 0: 환경 셋업 (venv 재생성 + dbt 프로젝트 스캐폴딩)

**Files:**
- Create: `dbt-poc/olist/dbt_project.yml`, `profiles.yml`, `.gitignore`, `commit.sh`, `README.md`
- Recreate: `dbt-poc/olist/.venv/` (uv)

- [ ] **Step 1: uv로 새 venv 생성 + dbt-duckdb 설치 (Python 3.12)**

기존 `dbt-poc/venv`는 이동되어 깨졌으므로 건드리지 않고, olist 전용 venv를 새로 만든다. uv가 Python 3.12를 자동 다운로드한다.

```bash
cd "/Users/n-mjkim/workspace2/dbt, datafusion/dbt-poc/olist"
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python dbt-duckdb
```
Expected: dbt-core 1.11.x + dbt-duckdb 1.11.x 설치 성공.
*폴백*: 3.12 설치 실패 시 `--python 3.11`로 재시도.

- [ ] **Step 2: dbt 동작 검증**

```bash
.venv/bin/dbt --version
```
Expected: `Core: 1.11.x`, `duckdb: 1.x` 출력, "bad interpreter" 없음.

- [ ] **Step 3: `dbt_project.yml` 작성**

```yaml
name: 'olist'
config-version: 2
version: '0.1'
profile: 'olist'

model-paths: ["models"]
seed-paths: ["seeds"]
snapshot-paths: ["snapshots"]
test-paths: ["tests"]
macro-paths: ["macros"]

target-path: "target"
clean-targets: ["target", "dbt_packages"]

require-dbt-version: [">=1.9.0", "<2.0.0"]

models:
  olist:
    staging:
      +materialized: view
      +docs: { node_color: "silver" }
    intermediate:
      +materialized: view
      +docs: { node_color: "#9ecae1" }
    marts:
      +materialized: table
      +docs: { node_color: "gold" }
    snapshot_src:
      +materialized: table

seeds:
  olist:
    +docs: { node_color: "#cd7f32" }
```

- [ ] **Step 4: `profiles.yml` 작성**

```yaml
olist:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: 'olist.duckdb'
      threads: 8
```

- [ ] **Step 5: `.gitignore` 작성**

```gitignore
.venv/
data/
*.duckdb
*.duckdb.wal
target/
logs/
dbt_packages/
commit.sh
**/.DS_Store
```

- [ ] **Step 6: `commit.sh` 작성 (dbt-study 동기화 헬퍼)**

```bash
#!/usr/bin/env bash
# 사용법: bash commit.sh "<commit message>"
set -e
MSG="$1"
SRC="/Users/n-mjkim/workspace2/dbt, datafusion"
STAGE="/tmp/dbt-study-stage"
EMAIL="121842688+10000JI@users.noreply.github.com"
[ -d "$STAGE/.git" ] || git clone -q https://github.com/10000JI/dbt-study.git "$STAGE"
mkdir -p "$STAGE/dbt-poc/olist"
rsync -a --delete \
  --exclude '.venv/' --exclude 'data/' --exclude 'target/' --exclude 'logs/' \
  --exclude 'dbt_packages/' --exclude '*.duckdb*' --exclude '.DS_Store' --exclude 'commit.sh' \
  "$SRC/dbt-poc/olist/" "$STAGE/dbt-poc/olist/"
cd "$STAGE"
git add -A
git -c user.name='10000JI' -c user.email="$EMAIL" commit -q -m "$MSG" || { echo "변경 없음"; exit 0; }
git push -q origin main
echo "pushed: $(git log -1 --format='%h %s')"
```

- [ ] **Step 7: `README.md` 작성 (데이터 다운로드 절차 포함)**

```markdown
# Olist 본편 dbt 파이프라인

## 데이터 준비 (수동)
1. https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce 에서 zip 다운로드
2. 압축 해제 후 아래 6개 CSV를 `data/`에 복사:
   - olist_orders_dataset.csv
   - olist_order_items_dataset.csv
   - olist_order_payments_dataset.csv
   - olist_products_dataset.csv
   - olist_customers_dataset.csv
   - product_category_name_translation.csv
3. 라이선스: CC BY-NC 4.0 (비상업 학습 전용). 원본 CSV는 git에 올리지 않음.

## 실행
```bash
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python dbt-duckdb
.venv/bin/dbt build --profiles-dir .
.venv/bin/dbt docs generate --profiles-dir .
```
```

- [ ] **Step 8: Commit**

```bash
bash commit.sh "chore(olist): 프로젝트 스캐폴딩 + venv 재생성 + 설정 파일"
```

---

## Task 1: 데이터 취득 검증

**Files:** (없음 — 사용자가 `data/`에 CSV 배치)

- [ ] **Step 1: 사용자에게 데이터 배치 요청**

README의 절차대로 6개 CSV를 `dbt-poc/olist/data/`에 두도록 안내. 배치 전까지 다음 스텝 대기.

- [ ] **Step 2: CSV 6종 존재 + 행수 검증**

```bash
cd "/Users/n-mjkim/workspace2/dbt, datafusion/dbt-poc/olist"
.venv/bin/python - <<'PY'
import duckdb, os
files = ["olist_orders_dataset","olist_order_items_dataset","olist_order_payments_dataset",
         "olist_products_dataset","olist_customers_dataset","product_category_name_translation"]
for f in files:
    p = f"data/{f}.csv"
    assert os.path.exists(p), f"MISSING: {p}"
    n = duckdb.sql(f"select count(*) from read_csv_auto('{p}')").fetchone()[0]
    print(f"{f}: {n} rows")
PY
```
Expected: orders ~99441, order_items ~112650, order_payments ~103886, products ~32951, customers ~99441, translation ~71. (정확한 수치는 버전에 따라 ±)

---

## Task 2: Sources (external CSV 선언)

**Files:**
- Create: `models/staging/_sources.yml`

- [ ] **Step 1: `_sources.yml` 작성**

```yaml
version: 2

sources:
  - name: olist
    description: "Olist Brazilian E-Commerce raw CSVs (external, read-only)."
    meta:
      external_location: "read_csv_auto('data/olist_{name}_dataset.csv', header = true, all_varchar = false)"
    tables:
      - name: orders
        description: "주문 헤더(상태·타임스탬프). PK: order_id"
      - name: order_items
        description: "주문 라인아이템. PK: order_id + order_item_id"
      - name: order_payments
        description: "주문 결제. PK: order_id + payment_sequential"
      - name: products
        description: "상품 마스터. PK: product_id"
      - name: customers
        description: "주문별 고객 키. PK: customer_id (customer_unique_id가 실인물)"
```

> `{name}`은 각 테이블명으로 치환됨(dbt-duckdb relation.py 확인 완료): `orders`→`olist_orders_dataset.csv`, `order_items`→`olist_order_items_dataset.csv` 등. `read_csv_auto(...)`는 괄호가 있어 따옴표 없이 그대로 FROM에 렌더된다.

- [ ] **Step 2: source 해석(컴파일) 검증**

```bash
.venv/bin/dbt compile --profiles-dir . -s 'source:olist+' 2>&1 | tail -5 || true
.venv/bin/dbt show --profiles-dir . --inline "select count(*) as n from {{ source('olist','orders') }}" --limit 1
```
Expected: 에러 없이 orders 행수(~99441) 출력 → external source가 CSV를 직접 읽음 확인.

- [ ] **Step 3: Commit**

```bash
bash commit.sh "feat(olist): external CSV source 선언 (_sources.yml)"
```

---

## Task 3: 카테고리 번역 Seed

**Files:**
- Create: `seeds/product_category_name_translation.csv` (data/에서 복사)

- [ ] **Step 1: seed 파일 배치 + 적재**

```bash
cp data/product_category_name_translation.csv seeds/
.venv/bin/dbt seed --profiles-dir .
```
Expected: `product_category_name_translation` seed 1개 PASS (~71행).

- [ ] **Step 2: 적재 검증**

```bash
.venv/bin/dbt show --profiles-dir . --inline "select count(*) n, count(distinct product_category_name) c from {{ ref('product_category_name_translation') }}" --limit 1
```
Expected: n≈71, c≈71.

- [ ] **Step 3: Commit**

```bash
bash commit.sh "feat(olist): 카테고리 영문명 번역 seed 추가"
```

---

## Task 4: Staging 레이어 (5 모델, view, 1:1)

**Files:**
- Create: `models/staging/stg_orders.sql`, `stg_order_items.sql`, `stg_products.sql`, `stg_payments.sql`, `stg_customers.sql`

- [ ] **Step 1: `stg_orders.sql`**

```sql
with source as (
    select * from {{ source('olist', 'orders') }}
),
renamed as (
    select
        order_id,
        customer_id,
        order_status,
        try_cast(order_purchase_timestamp as timestamp)      as order_purchase_at,
        try_cast(order_approved_at as timestamp)             as order_approved_at,
        try_cast(order_delivered_carrier_date as timestamp)  as order_delivered_carrier_at,
        try_cast(order_delivered_customer_date as timestamp) as order_delivered_customer_at,
        try_cast(order_estimated_delivery_date as timestamp) as order_estimated_delivery_at,
        try_cast(order_purchase_timestamp as date)           as order_purchase_date
    from source
)
select * from renamed
```

- [ ] **Step 2: `stg_order_items.sql`**

```sql
with source as (
    select * from {{ source('olist', 'order_items') }}
),
renamed as (
    select
        order_id,
        cast(order_item_id as integer)        as order_item_number,
        product_id,
        seller_id,
        try_cast(shipping_limit_date as timestamp) as shipping_limit_at,
        cast(price as double)                 as item_price,
        cast(freight_value as double)         as freight_value
    from source
)
select * from renamed
```

- [ ] **Step 3: `stg_products.sql`**

```sql
with source as (
    select * from {{ source('olist', 'products') }}
),
renamed as (
    select
        product_id,
        product_category_name,
        cast(product_weight_g as double)  as product_weight_g,
        cast(product_length_cm as double) as product_length_cm,
        cast(product_height_cm as double) as product_height_cm,
        cast(product_width_cm as double)  as product_width_cm
    from source
)
select * from renamed
```

- [ ] **Step 4: `stg_payments.sql`**

```sql
with source as (
    select * from {{ source('olist', 'order_payments') }}
),
renamed as (
    select
        order_id,
        cast(payment_sequential as integer)   as payment_sequential,
        payment_type,
        cast(payment_installments as integer) as payment_installments,
        cast(payment_value as double)         as payment_value
    from source
)
select * from renamed
```

- [ ] **Step 5: `stg_customers.sql`**

```sql
with source as (
    select * from {{ source('olist', 'customers') }}
),
renamed as (
    select
        customer_id,
        customer_unique_id,
        cast(customer_zip_code_prefix as varchar) as customer_zip_code_prefix,
        customer_city,
        customer_state
    from source
)
select * from renamed
```

- [ ] **Step 6: staging 5종 빌드**

```bash
.venv/bin/dbt run --profiles-dir . -s staging
```
Expected: 5 view models PASS.

- [ ] **Step 7: 그레인·행수 검증**

```bash
.venv/bin/dbt show --profiles-dir . --inline "
select 'orders' t, count(*) n, count(distinct order_id) k from {{ ref('stg_orders') }}
union all select 'customers', count(*), count(distinct customer_id) from {{ ref('stg_customers') }}
union all select 'products', count(*), count(distinct product_id) from {{ ref('stg_products') }}" --limit 10
```
Expected: orders n=k(order_id 유일), customers n=k, products n=k.

- [ ] **Step 8: Commit**

```bash
bash commit.sh "feat(olist): staging 5종 (orders/order_items/products/payments/customers)"
```

---

## Task 5: Staging 테스트 (generic, arguments 신문법)

**Files:**
- Create: `models/staging/_staging.yml`

- [ ] **Step 1: `_staging.yml` 작성**

```yaml
version: 2

models:
  - name: stg_orders
    columns:
      - name: order_id
        tests: [unique, not_null]
      - name: customer_id
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('stg_customers')
                field: customer_id
      - name: order_status
        tests:
          - accepted_values:
              arguments:
                values: ['delivered','shipped','canceled','unavailable','invoiced','processing','created','approved']

  - name: stg_customers
    columns:
      - name: customer_id
        tests: [unique, not_null]
      - name: customer_unique_id
        tests: [not_null]

  - name: stg_products
    columns:
      - name: product_id
        tests: [unique, not_null]

  - name: stg_payments
    columns:
      - name: order_id
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('stg_orders')
                field: order_id
      - name: payment_type
        tests:
          - accepted_values:
              arguments:
                values: ['credit_card','boleto','voucher','debit_card','not_defined']

  - name: stg_order_items
    columns:
      - name: order_id
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('stg_orders')
                field: order_id
      - name: product_id
        tests: [not_null]
```

- [ ] **Step 2: staging 테스트 실행**

```bash
.venv/bin/dbt test --profiles-dir . -s staging
```
Expected: 전부 PASS. (relationships가 실패하면 데이터 정합성 이슈 → 로그에 기록 후 해당 테스트를 `config: {severity: warn}`로 완화하고 정오표에 남긴다.)

- [ ] **Step 3: Commit**

```bash
bash commit.sh "test(olist): staging generic 테스트 (unique/not_null/relationships/accepted_values)"
```

---

## Task 6: Intermediate (`int_order_items_enriched`)

**Files:**
- Create: `models/intermediate/int_order_items_enriched.sql`, `models/intermediate/_intermediate.yml`

- [ ] **Step 1: `int_order_items_enriched.sql` (grain: order_item)**

```sql
with items as (
    select * from {{ ref('stg_order_items') }}
),
products as (
    select * from {{ ref('stg_products') }}
),
category as (
    select * from {{ ref('product_category_name_translation') }}
)
select
    items.order_id,
    items.order_item_number,
    items.product_id,
    items.seller_id,
    products.product_category_name,
    coalesce(category.product_category_name_english, products.product_category_name) as product_category,
    items.item_price,
    items.freight_value,
    items.item_price + items.freight_value as item_total
from items
left join products on items.product_id = products.product_id
left join category on products.product_category_name = category.product_category_name
```

- [ ] **Step 2: `_intermediate.yml`**

```yaml
version: 2
models:
  - name: int_order_items_enriched
    description: "주문 라인아이템 + 상품 카테고리(영문) 결합. grain: order_id + order_item_number"
    columns:
      - name: order_id
        tests: [not_null]
      - name: item_total
        tests: [not_null]
```

- [ ] **Step 3: 빌드 + 그레인 검증**

```bash
.venv/bin/dbt build --profiles-dir . -s int_order_items_enriched
.venv/bin/dbt show --profiles-dir . --inline "select count(*) n, count(distinct order_id||'-'||order_item_number) k from {{ ref('int_order_items_enriched') }}" --limit 1
```
Expected: 빌드 PASS, n=k (order_id+order_item_number 유일 → 조인으로 행 증식 없음 확인).

- [ ] **Step 4: Commit**

```bash
bash commit.sh "feat(olist): intermediate int_order_items_enriched (아이템+카테고리 조인)"
```

---

## Task 7: Marts — Dimensions

**Files:**
- Create: `models/marts/dim_customers.sql`, `models/marts/dim_products.sql`

- [ ] **Step 1: `dim_customers.sql` (grain: customer_id)**

```sql
select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
from {{ ref('stg_customers') }}
```

- [ ] **Step 2: `dim_products.sql` (grain: product_id)**

```sql
with products as (
    select * from {{ ref('stg_products') }}
),
category as (
    select * from {{ ref('product_category_name_translation') }}
)
select
    products.product_id,
    products.product_category_name,
    coalesce(category.product_category_name_english, products.product_category_name) as product_category,
    products.product_weight_g,
    products.product_length_cm,
    products.product_height_cm,
    products.product_width_cm
from products
left join category on products.product_category_name = category.product_category_name
```

- [ ] **Step 3: 빌드**

```bash
.venv/bin/dbt run --profiles-dir . -s dim_customers dim_products
```
Expected: 2 table models PASS.

- [ ] **Step 4: Commit**

```bash
bash commit.sh "feat(olist): marts dim_customers, dim_products"
```

---

## Task 8: Marts — Facts

**Files:**
- Create: `models/marts/fct_orders.sql`, `models/marts/fct_daily_sales.sql`

- [ ] **Step 1: `fct_orders.sql` (grain: order_id)**

```sql
with orders as (
    select * from {{ ref('stg_orders') }}
),
items as (
    select
        order_id,
        count(*)                    as items_count,
        count(distinct product_id)  as distinct_products,
        sum(item_price)             as gross_item_value,
        sum(freight_value)          as freight_value
    from {{ ref('int_order_items_enriched') }}
    group by order_id
),
payments as (
    select
        order_id,
        sum(payment_value) as payment_value,
        count(*)           as payment_count
    from {{ ref('stg_payments') }}
    group by order_id
)
select
    orders.order_id,
    orders.customer_id,
    orders.order_status,
    orders.order_purchase_at,
    orders.order_purchase_date,
    coalesce(items.items_count, 0)        as items_count,
    coalesce(items.distinct_products, 0)  as distinct_products,
    coalesce(items.gross_item_value, 0)   as gross_item_value,
    coalesce(items.freight_value, 0)      as freight_value,
    coalesce(payments.payment_value, 0)   as payment_value
from orders
left join items    on orders.order_id = items.order_id
left join payments on orders.order_id = payments.order_id
```

- [ ] **Step 2: `fct_daily_sales.sql` (grain: order_purchase_date)**

```sql
select
    order_purchase_date,
    count(*)                   as orders_count,
    count(distinct customer_id) as distinct_customers,
    sum(gross_item_value)      as gross_item_value,
    sum(freight_value)         as freight_value,
    sum(payment_value)         as payment_value
from {{ ref('fct_orders') }}
where order_purchase_date is not null
group by order_purchase_date
```

- [ ] **Step 3: 빌드 + 그레인 검증**

```bash
.venv/bin/dbt run --profiles-dir . -s fct_orders fct_daily_sales
.venv/bin/dbt show --profiles-dir . --inline "select count(*) n, count(distinct order_id) k from {{ ref('fct_orders') }}" --limit 1
```
Expected: 2 table models PASS, fct_orders n=k (주문 1행 그레인).

- [ ] **Step 4: Commit**

```bash
bash commit.sh "feat(olist): marts fct_orders, fct_daily_sales"
```

---

## Task 9: Marts 테스트 (generic + singular)

**Files:**
- Create: `models/marts/_marts.yml`, `tests/assert_fct_orders_amounts_non_negative.sql`

- [ ] **Step 1: `_marts.yml`**

```yaml
version: 2
models:
  - name: fct_orders
    description: "주문 1행 팩트(상태·금액·결제)."
    columns:
      - name: order_id
        tests: [unique, not_null]
      - name: customer_id
        tests:
          - not_null
          - relationships:
              arguments:
                to: ref('dim_customers')
                field: customer_id
  - name: fct_daily_sales
    columns:
      - name: order_purchase_date
        tests: [unique, not_null]
  - name: dim_customers
    columns:
      - name: customer_id
        tests: [unique, not_null]
  - name: dim_products
    columns:
      - name: product_id
        tests: [unique, not_null]
```

- [ ] **Step 2: singular test `tests/assert_fct_orders_amounts_non_negative.sql`**

```sql
-- 실패 = 금액 음수 행이 존재. 0행이면 PASS.
select order_id, gross_item_value, freight_value, payment_value
from {{ ref('fct_orders') }}
where gross_item_value < 0
   or freight_value < 0
   or payment_value < 0
```

- [ ] **Step 3: 마트 테스트 실행**

```bash
.venv/bin/dbt test --profiles-dir . -s marts fct_orders fct_daily_sales dim_customers dim_products assert_fct_orders_amounts_non_negative
```
Expected: 전부 PASS.

- [ ] **Step 4: Commit**

```bash
bash commit.sh "test(olist): marts generic + singular(금액 비음수) 테스트"
```

---

## Task 10: 전체 `dbt build` + SKIP 게이트 재현

**Files:** (임시 수정 → 복구)

- [ ] **Step 1: 전체 build**

```bash
.venv/bin/dbt build --profiles-dir .
```
Expected: 모든 seed/model/test PASS, ERROR=0. 실행 순서가 source→staging(view)→int→marts(table)→test로 위상정렬됨을 로그로 확인.

- [ ] **Step 2: 일부러 테스트 깨서 SKIP 게이트 관찰**

`models/staging/_staging.yml`의 stg_orders.order_status accepted_values에서 `'delivered'`를 **임시 제거** → delivered 주문이 위반 → 테스트 실패.

```bash
.venv/bin/dbt build --profiles-dir . -s stg_orders+
```
Expected: stg_orders의 accepted_values 테스트 **FAIL** → 하위(int/fct 등) **SKIP** 발생. 로그에서 `SKIP` 라인 확인 → 이론 7.1 "상위 실패→하위 SKIP" 재현.

- [ ] **Step 3: 복구 후 재검증**

`'delivered'`를 다시 넣고:
```bash
.venv/bin/dbt build --profiles-dir .
```
Expected: 다시 전부 PASS.

- [ ] **Step 4: Commit**

```bash
bash commit.sh "test(olist): 전체 build 통과 + SKIP 게이트 재현 관찰"
```

---

## Task 11: Snapshot (SCD2) 통제 실습

**Files:**
- Create: `models/snapshot_src/snap_orders_src.sql`, `snapshots/orders_snapshot.yml`

- [ ] **Step 1: mutable 소스 테이블 `snap_orders_src.sql`**

```sql
{{ config(materialized='table') }}
-- SCD2 실습용 소형 변경가능 테이블 (status가 'shipped'인 주문 200건)
select order_id, order_status
from {{ ref('stg_orders') }}
where order_status = 'shipped'
order by order_id
limit 200
```

- [ ] **Step 2: snapshot 정의 `snapshots/orders_snapshot.yml`**

```yaml
snapshots:
  - name: orders_snapshot
    relation: ref('snap_orders_src')
    config:
      schema: snapshots
      unique_key: order_id
      strategy: check
      check_cols: ['order_status']
```

- [ ] **Step 3: 소스 빌드 + 1차 snapshot**

```bash
.venv/bin/dbt run --profiles-dir . -s snap_orders_src
.venv/bin/dbt snapshot --profiles-dir .
.venv/bin/dbt show --profiles-dir . --inline "select count(*) n, count(distinct order_id) k, sum(case when dbt_valid_to is null then 1 else 0 end) current_rows from {{ ref('orders_snapshot') }}" --limit 1
```
Expected: n=k=200, current_rows=200 (모두 valid_to NULL = 현재행).

- [ ] **Step 4: 한 주문 status 변경 (직접 UPDATE)**

```bash
.venv/bin/python - <<'PY'
import duckdb
con = duckdb.connect('olist.duckdb')
oid = con.sql("select order_id from snap_orders_src order by order_id limit 1").fetchone()[0]
con.sql(f"update snap_orders_src set order_status='delivered' where order_id='{oid}'")
print("mutated:", oid, "→ delivered")
con.close()
PY
```
> 주의: 이 실습 동안 `dbt run -s snap_orders_src`를 다시 돌리면 테이블이 재생성되어 변경이 사라진다. snapshot만 다시 돌릴 것.

- [ ] **Step 5: 2차 snapshot → SCD2 관찰**

```bash
.venv/bin/dbt snapshot --profiles-dir .
.venv/bin/dbt show --profiles-dir . --inline "select order_id, order_status, dbt_valid_from, dbt_valid_to from {{ ref('orders_snapshot') }} where order_id in (select order_id from {{ ref('orders_snapshot') }} group by order_id having count(*)>1)" --limit 10
```
Expected: 변경된 order_id가 **2행** — 옛 행(shipped, dbt_valid_to 채워짐) + 새 행(delivered, dbt_valid_to NULL). dbt_valid_from/to로 이력 추적 확인 → 이론 5.4 SCD2 검증 완료.

- [ ] **Step 6: Commit**

```bash
bash commit.sh "feat(olist): snapshot SCD2 통제 실습 (check 전략, status 변경 관찰)"
```

---

## Task 12: 문서·계보 + 노트 갱신

**Files:**
- Modify: `dbt-poc/실습로그.md`, `dbt (이론).md`

- [ ] **Step 1: docs 생성 + lineage 확인**

```bash
.venv/bin/dbt docs generate --profiles-dir .
.venv/bin/python - <<'PY'
import json
m = json.load(open('target/manifest.json'))
pm = m['parent_map']
for k in sorted(pm):
    if k.startswith(('model.olist','snapshot.olist')):
        print(k.split('.')[-1], '<=', [p.split('.')[-1] for p in pm[k]])
PY
```
Expected: source→stg→int→marts 의존이 parent_map에 나타남(예: `fct_orders <= [stg_orders, int_order_items_enriched, stg_payments]`).

- [ ] **Step 2: `dbt-poc/실습로그.md`에 STEP 4~ 이어쓰기**

Olist 본편 결과 추가: source() 적재, staging→int→marts 행수/그레인, 테스트 PASS 수, SKIP 게이트 재현, SCD2 관찰, lineage. 실제 관찰 수치로 기록(가짜 수치 금지).

- [ ] **Step 3: `dbt (이론).md`의 "미검증" 꼬리표 제거/갱신**

다음 항목을 Olist 검증 결과로 갱신: 5.2 source()/freshness, 5.4 snapshots SCD2, 5.5 singular test, 7.1 SKIP 게이트, 9.x intermediate 레이어. 각 🔬 실습 검증 블록에 "Olist 본편에서 확인" 추가.

- [ ] **Step 4: Commit (노트 동기화)**

```bash
# 실습로그/이론.md는 olist/ 밖이므로 기존 전체 동기화 경로로 푸시
SRC="/Users/n-mjkim/workspace2/dbt, datafusion"; STAGE="/tmp/dbt-study-stage"
EMAIL="121842688+10000JI@users.noreply.github.com"
cp "$SRC/dbt (이론).md" "$STAGE/dbt (이론).md"
cp "$SRC/dbt-poc/실습로그.md" "$STAGE/dbt-poc/실습로그.md"
cd "$STAGE" && git add -A
git -c user.name='10000JI' -c user.email="$EMAIL" commit -q -m "docs(olist): 실습로그 STEP4~ + 이론 미검증 항목 갱신"
git push -q origin main && echo "pushed: $(git log -1 --format='%h %s')"
```

---

## Self-Review (작성자 체크)

**1. Spec coverage:**
- §3 환경 셋업 → Task 0 ✅ · §4 아키텍처 → Task 2~8 ✅ · §5.1 sources → Task 2 ✅ · §5.1 카테고리 seed → Task 3 ✅ · §5.2 staging → Task 4 ✅ · §5.3 intermediate → Task 6 ✅ · §5.4 marts → Task 7,8 ✅ · §6 테스트(generic+singular+SKIP) → Task 5,9,10 ✅ · §7 snapshot SCD2 → Task 11 ✅ · §8 문서·로그·노트 → Task 12 ✅ · §9 라이선스/레포(gitignore data,*.duckdb) → Task 0 ✅ · §1 성공기준 → Task 10(build), 11(SCD2), 12(lineage) ✅.
- freshness(§5.1 선택)는 정적 데이터라 "개념 확인" 수준 — Phase 1 필수 아님, Task 12 노트에서 한계 명시로 처리.

**2. Placeholder scan:** TBD/TODO 없음. 모든 코드 스텝에 실제 SQL/YAML/명령 포함.

**3. Type/이름 일관성:**
- staging 산출 컬럼명(`order_purchase_date`, `item_price`, `freight_value`, `item_total`, `payment_value`)이 int/marts에서 동일하게 참조됨 ✅
- `int_order_items_enriched`의 grain 키(`order_id`+`order_item_number`)가 Task 6 검증과 일치 ✅
- ref 이름(`product_category_name_translation`, `stg_*`, `int_*`, `fct_*`, `dim_*`)이 전 태스크 일관 ✅
- snapshot `relation: ref('snap_orders_src')` ↔ Task 11 Step 1 모델명 일치 ✅
