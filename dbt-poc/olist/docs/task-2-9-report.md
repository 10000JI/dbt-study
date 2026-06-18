# Task 2-9 구현 보고서

**작성일**: 2026-06-18  
**구현자**: Claude Code (claude-sonnet-4-6)  
**작업 범위**: Task 2 ~ Task 9 (모델 레이어 전체 + 테스트)

---

## 1. 만든 파일 목록

### Task 2: Sources
- `models/staging/_sources.yml` — external CSV source 선언 (5종)

### Task 3: Seed
- `seeds/product_category_name_translation.csv` — `data/`에서 복사

### Task 4: Staging 모델 (5종, materialized=view)
- `models/staging/stg_orders.sql`
- `models/staging/stg_order_items.sql`
- `models/staging/stg_products.sql`
- `models/staging/stg_payments.sql`
- `models/staging/stg_customers.sql`

### Task 5: Staging 테스트
- `models/staging/_staging.yml` — generic 테스트 16종 (unique/not_null/relationships/accepted_values)

### Task 6: Intermediate
- `models/intermediate/int_order_items_enriched.sql`
- `models/intermediate/_intermediate.yml`

### Task 7: Marts — Dimensions
- `models/marts/dim_customers.sql`
- `models/marts/dim_products.sql`

### Task 8: Marts — Facts
- `models/marts/fct_orders.sql`
- `models/marts/fct_daily_sales.sql`

### Task 9: Marts 테스트 + Singular Test
- `models/marts/_marts.yml` — generic 테스트 11종
- `tests/assert_fct_orders_amounts_non_negative.sql` — singular test (금액 비음수)

---

## 2. `dbt build` 최종 요약

```
dbt build --profiles-dir .
```

| 항목 | 수 |
|------|----|
| PASS | 40 |
| WARN | 0  |
| ERROR | 0 |
| SKIP | 0  |
| NO-OP | 0 |
| **TOTAL** | **40** |

구성:
- 1 seed (product_category_name_translation: INSERT 71)
- 6 view models (5 staging + 1 intermediate)
- 4 table models (2 dim + 2 fct)
- 29 data tests (16 staging + 2 intermediate + 11 marts/singular)

---

## 3. 모델별 행수

| 모델 | 행수 |
|------|------|
| stg_orders | 99,441 |
| stg_order_items | 112,650 |
| stg_products | 32,951 |
| stg_payments | 103,886 |
| stg_customers | 99,441 |
| int_order_items_enriched | 112,650 |
| dim_customers | 99,441 |
| dim_products | 32,951 |
| fct_orders | 99,441 |
| fct_daily_sales | 634 |
| product_category_name_translation (seed) | 71 |

---

## 4. 그레인 검증 결과

### fct_orders (grain: order_id)
```
count(*) n = 99441
count(distinct order_id) k = 99441
→ n = k ✅ 주문 1행 그레인 확인
```

### int_order_items_enriched (grain: order_id + order_item_number)
```
count(*) n = 112650
count(distinct order_id||'-'||order_item_number) k = 112650
→ n = k ✅ (order_id, order_item_number) 복합키 유일 확인, 조인 행 증식 없음
```

### 추가 검증 (staging)
```
stg_orders: n=99441, distinct order_id=99441 → 유일 ✅
stg_customers: n=99441, distinct customer_id=99441 → 유일 ✅
stg_products: n=32951, distinct product_id=32951 → 유일 ✅
```

---

## 5. warn으로 완화한 테스트

**없음.** 모든 29개 테스트가 실데이터에서 PASS로 통과했다.

- relationships 테스트 3종 (stg_payments→stg_orders, stg_order_items→stg_orders, stg_orders→stg_customers) 모두 PASS — 고아키 없음
- accepted_values 테스트 2종 (stg_orders.order_status, stg_payments.payment_type) 모두 PASS — 미등록 값 없음
- singular test (assert_fct_orders_amounts_non_negative) PASS — 음수 금액 행 없음
- fct_orders.relationships→dim_customers PASS — 마트 수준 참조 무결성 확인

---

## 6. 이탈/막힌 점

- **이탈 없음.** 계획 파일의 SQL/YAML을 그대로 사용하여 Task 2~9를 완료했다.
- `dbt_project.yml`에 `models.olist.snapshot_src` 경로가 선언되어 있지만 Task 2~9 범위에는 해당 모델 없어 WARNING이 표시됨. 이는 Task 11(Snapshot) 구현 전까지 정상적인 동작이며, 기능에 영향 없음.
- 실데이터(Olist)에서 데이터 품질 이슈 없음 — 모든 관계형 테스트가 에러 없이 통과.
