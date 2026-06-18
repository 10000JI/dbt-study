# Olist dbt 파이프라인 (Phase 1) — 최종 리뷰

> 리뷰일: 2026-06-18 · 관점: 정확성·스펙 준수 · 상태: `dbt build` PASS=40
> 대조 스펙: `docs/2026-06-16-olist-pipeline-design.md`, `docs/2026-06-16-olist-pipeline-plan.md`

## 요약

| 심각도 | 건수 |
|---|---|
| Critical | 0 |
| Important | 2 |
| Minor | 4 |

핵심 모델링 정확성(그레인, fan-out, 금액 출처, coalesce)은 **모두 올바르다**. 발견된 문제는 전부 **테스트 커버리지/스펙 준수** 영역이며, 산출 데이터값의 오류는 없다.

---

## 점검 항목별 판정 (요청된 5개 정확성 포인트)

### 1. Fan-out / 그레인 버그 — 문제 없음 ✅
`models/marts/fct_orders.sql:4-21` — `items`와 `payments`를 각각 `group by order_id`로 **사전 집계한 CTE**로 만든 뒤, `orders`에 left join한다(`:34-35`). 두 CTE 모두 order_id가 유일하므로 join 시 행 증식(뻥튀기)이 없다. 계획(plan Task 8 Step 1)과 정확히 일치. `fct_orders` 그레인 = 주문 1행 보장.

### 2. 금액 집계 정확성 — 문제 없음 ✅
- `gross_item_value` = `sum(item_price)` (아이템 금액, int 그레인 출처) — `fct_orders.sql:9`
- `freight_value` = `sum(freight_value)` (배송비, int 출처) — `:10`
- `payment_value` = `sum(payment_value)` (결제 금액, stg_payments 출처) — `:17`

아이템 금액과 결제 금액이 **각각 올바른 출처에서 분리 집계**되며 혼동 없음. `item_total = item_price + freight_value`는 int에서만 파생(`int_order_items_enriched.sql:19`)되고 fct_orders에서는 사용하지 않으므로 freight 이중계상 위험도 없다.

### 3. Left join 누락 처리 — 문제 없음 ✅
아이템/결제 없는 주문(예: status=`unavailable`/`canceled`로 라인아이템 미존재, 결제 누락)에 대해 `items_count`, `distinct_products`, `gross_item_value`, `freight_value`, `payment_value` 전부 `coalesce(..., 0)` 적용(`fct_orders.sql:28-32`). NULL 누수 없음.

### 4. 테스트 적정성 — 부분 미흡 (Important #1, #2 참조)
PK 유일성은 단일키 PK(order_id, customer_id, product_id, order_purchase_date)에는 모두 적용. 그러나 **복합키 그레인(order_items, payments, intermediate)의 유일성 검증이 비어 있음** → 검증 공백.

### 5. 스펙 이탈 — 1건 (Important #2: singular 테스트 축소 구현)

---

## Important

### [Important #1] 복합키 그레인 유일성 검증 공백
**파일:** `models/staging/_staging.yml:48-58`, `models/intermediate/_intermediate.yml:5-9`

**근거:**
- `stg_order_items` 그레인 = `order_id + order_item_number`(설계 §5.1 PK). `_staging.yml`에는 order_id(not_null/relationships), product_id(not_null)만 있고 **복합키 유일성 테스트가 없다**. order_item_number 자체에 대한 테스트도 없다.
- `stg_payments` 그레인 = `order_id + payment_sequential`(설계 §5.1 PK). 마찬가지로 복합키 유일성 미검증. payment_sequential 컬럼 테스트 없음.
- `int_order_items_enriched` 그레인 = `order_id + order_item_number`(_intermediate.yml:4 설명에 명시). 그러나 테스트는 order_id(not_null), item_total(not_null)뿐 — **그레인 유일성 미검증**. plan Task 6 Step 3에서 `n=k`를 수동 `dbt show`로만 확인했고, 영구 테스트로 고정되지 않았다.

이것이 문제인 이유: 상류 join 로직이 깨져 행이 증식해도(예: int의 `left join products`가 product 중복으로 fan-out 나면) **자동 테스트로 잡히지 않는다**. fct_orders의 그레인은 group by로 강제되므로 최종 산출은 안전하지만, 중간 단계 회귀를 탐지할 안전망이 없다.

**권고:** dbt_utils의 `unique_combination_of_columns` 테스트를 추가하거나(패키지 도입 필요), 최소한 각 모델에 model-level 복합키 검증을 추가:
```yaml
# _staging.yml — stg_order_items, stg_payments 각각
    tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns: [order_id, order_item_number]  # payments는 [order_id, payment_sequential]
```
패키지 도입을 피하려면 `tests/`에 singular 테스트(`group by ... having count(*)>1`)로 대체 가능. 학습 프로젝트이므로 **최소 1개 모델(int)에라도 복합키 유일성 테스트를 명시**해 개념을 체득할 것을 권고.

### [Important #2] Singular 테스트가 스펙(설계 §6)보다 축소 구현됨
**파일:** `tests/assert_fct_orders_amounts_non_negative.sql:4-6`

**근거:** 설계 §6 (design line 86)의 singular 테스트 계약은:
> "결제 정합성 — `fct_orders`에서 `payment_value < 0` **또는 (아이템 있는데 결제 0)**인 행이 있으면 실패."

현재 구현은 `gross_item_value < 0 OR freight_value < 0 OR payment_value < 0` (음수 검사)만 한다. 설계가 명시한 **"아이템이 있는데 결제가 0"(items_count > 0 AND payment_value = 0)** 정합성 조건이 빠졌다. plan Task 9 Step 2는 음수만 검사하도록 약화되어 있어 plan↔design 간 불일치이며, 구현은 plan을 따랐다.

참고로 음수 검사 자체도 Olist 금액이 비음수라 항상 PASS → 사실상 회귀 탐지력이 약하다. design이 의도한 "아이템 있는데 결제 0" 조건이 실제로 결제 누락 주문을 잡아내는 더 의미 있는 정합성 테스트였다.

**권고:** design 의도대로 정합성 절을 추가:
```sql
select order_id, gross_item_value, freight_value, payment_value, items_count
from {{ ref('fct_orders') }}
where gross_item_value < 0
   or freight_value < 0
   or payment_value < 0
   or (items_count > 0 and payment_value = 0)
```
주의: Olist 실데이터에 아이템 있는데 결제 0인 주문이 실재할 수 있으므로(소수의 결제 누락 주문 존재), 추가 시 `dbt build`가 FAIL할 가능성이 있다. 그 경우 design 의도대로 **실패를 관찰**한 뒤 `config: {severity: warn}`로 완화하거나 정오표에 기록하는 것이 학습 목적에 부합한다. 파일명(`assert_fct_orders_amounts_non_negative`)도 음수 검사만 반영하므로, 정합성 절을 넣으면 이름이 내용과 어긋난다 — 이름 유지 시 별도 singular 테스트로 분리 권고.

---

## Minor

### [Minor #1] order_status accepted_values와 누락 가능성
**파일:** `models/staging/_staging.yml:15-19`
`order_status` accepted_values 목록은 Olist 표준 8개 상태와 일치하며 적절. 다만 이 목록이 SKIP 게이트 재현(plan Task 10)에 쓰이는 검증 도구이므로, 향후 데이터 갱신 시 신규 상태가 들어오면 의미상 False positive가 날 수 있음. 현 데이터엔 문제 없음. 조치 불필요(참고용).

### [Minor #2] stg_payments.payment_type relationships 미적용 (의도된 누락)
**파일:** `models/staging/_staging.yml:42-46`
payment_type은 accepted_values만 검사. `not_defined` 등 희소 타입 포함 목록은 적절. relationships 대상이 없으므로 정상. 조치 불필요.

### [Minor #3] dim_products 그레인 유일성은 검증되나 카테고리 join 무결성은 미검증
**파일:** `models/marts/dim_products.sql:16`, `_marts.yml:23-26`
`left join category on products.product_category_name = category.product_category_name`. product_id 유일성 테스트는 있으나, category seed에 중복 `product_category_name`이 있으면 dim_products가 fan-out될 수 있다. seed는 번역 룩업(~71행, 카테고리당 1행 가정)이라 실제 위험은 낮음. product_id unique 테스트가 사실상 이 fan-out을 간접 차단하므로 안전. 동일 join이 `int_order_items_enriched.sql:22`에도 있는데 거기엔 그레인 유일성 테스트가 없음(Important #1과 연결). 참고용.

### [Minor #4] int 모델 그레인 설명-테스트 불일치 (문서 정확성)
**파일:** `models/intermediate/_intermediate.yml:4`
description에 "grain: order_id + order_item_number"라고 계약을 명시했으나 이를 강제하는 테스트가 없다(Important #1). 문서상 계약과 실제 검증의 간극. Important #1 해소 시 함께 정리됨.

---

## 스펙 준수 종합

| 스펙 요구 | 구현 | 판정 |
|---|---|---|
| staging = raw 1:1 (view) | stg_* 5종, rename/cast만 | ✅ |
| intermediate = order_item 그레인 조인 | int_order_items_enriched, left join products/category | ✅ |
| marts = table | dbt_project.yml 설정(plan) + 4 모델 | ✅ |
| fct_orders 그레인 = order_id 유일 | group by 사전집계 후 join | ✅ (테스트로도 검증됨) |
| int 그레인 = order_id+order_item_number | 구현됨 | ⚠️ 테스트 공백(Important #1) |
| generic 4종 (arguments 신문법) | unique/not_null/relationships/accepted_values 모두 `arguments:` 래퍼 | ✅ |
| singular 테스트 | 존재하나 정합성 절 누락 | ⚠️ 축소(Important #2) |
| 복합키 유일성 | order_items/payments/int 미검증 | ⚠️ 공백(Important #1) |

**계획에 없는 추가물**: 발견되지 않음.
**빠진 요구사항**: 복합키 유일성 테스트(Important #1), singular 정합성 절(Important #2).

---

## 결론
모델링 정확성(fan-out 없음, 금액 출처 정확, coalesce 완비, 그레인 보장)은 **합격**. Critical 없음. 학습 프로젝트의 핵심 목표(intermediate·singular·generic 신문법·SCD2 체득)는 달성됐으나, **테스트 안전망 2가지(복합키 유일성, singular 정합성 절)**를 보강하면 회귀 탐지력과 design 스펙 준수가 완성된다.
