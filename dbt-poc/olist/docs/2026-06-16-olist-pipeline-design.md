# Olist 본편 파이프라인 — 설계 문서 (Design Spec)

> 작성일: 2026-06-16 · 상태: **승인됨**(브레인스토밍 완료) · 다음 단계: writing-plans
> 선행: `데이터셋 Track A — 1차 학습.md`(§2 Olist 본편) · `dbt (이론).md` · `dbt-poc/실습로그.md`
> 목적: jaffle 워밍업에서 못 다룬 개념(`source()`+freshness · intermediate 레이어 · singular 테스트 · snapshots SCD2 · 상위실패→하위 SKIP 게이트)을 **실데이터 Olist로 직접 작성하며 체득**한다.

---

## 1. 목표 & 성공 기준

Track A 1차 완료 기준(→ 2차 전환)을 Olist로 충족한다:

- [ ] Olist로 **staging→intermediate→marts** 구성 + **generic/singular 테스트**
- [ ] **snapshots(SCD2)** 1회 관찰 · `dbt docs`로 **lineage** 확인
- [ ] 이론 노트의 "미검증" 꼬리표 제거: `source()`/freshness, intermediate, singular test, SCD2, SKIP 게이트

**성공 판정**: `dbt build` 통과(모델+테스트) · lineage(source→stg→int→mart) 생성 · 결제/매출 집계 정합성 확인 · SCD2 이력 1행 관찰.

## 2. 확정된 결정 (브레인스토밍)

| 항목 | 결정 | 근거 |
|---|---|---|
| 데이터 취득 | **수동 다운로드 후 전달** | Kaggle 자격증명 셋업 회피, 가장 빠름 |
| 범위 | **단계적** — 핵심 5테이블 끝까지(Phase 1) → 확장(Phase 2) | 모든 개념을 확실히 완주 후 넓힘 |
| 적재 방식 | **`source()`로 제대로** (dbt-duckdb external CSV) | 이론 5.2/9.2 "미검증 source()" 체득 + 실무(raw 이미 적재) 패턴 |

## 3. 환경 셋업 (전제)

- **venv 재생성**: 기존 venv는 `test_20260603`에서 이동되어 shebang 깨짐(`bad interpreter`). `uv`로 신규 생성.
  - **Python 3.13** + 최신 `dbt-duckdb` 우선. 3.13에서 dbt 설치 이슈 시 **3.9로 폴백**(기존 검증된 조합: dbt-core 1.10.22 + dbt-duckdb 1.10.0).
  - 우리가 `dbt_project.yml`을 작성하므로 `require-dbt-version`을 설치 버전에 맞춰 지정 → **`--no-version-check` 불필요**(jaffle만 1.11 요구였음).
- **신규 dbt 프로젝트**: `dbt-poc/olist/` (jaffle 미수정). DB 파일 `olist.duckdb`. profiles.yml은 프로젝트 로컬(`type: duckdb`).

## 4. 아키텍처 — Phase 1 (핵심 5 테이블)

```
raw (CSV via source)        staging (view, 1:1)     intermediate            marts
─────────────────────       ───────────────────     ─────────────────       ──────────────────────
olist_orders            →   stg_orders          ┐
olist_order_items       →   stg_order_items     ├→  int_order_items_     ┐
olist_products          →   stg_products        ┘   enriched             ├→  fct_orders       (주문 1행)
olist_order_payments    →   stg_payments        ────────────────────────┤   fct_daily_sales   (일자 집계)
olist_customers         →   stg_customers       ────────────────────────┴→  dim_customers
                                                                             dim_products
```

3계층 + `stg_`/`int_`/`fct_`/`dim_` 네이밍 — jaffle엔 없던 **intermediate를 처음 직접 작성**(이론 9장 검증).

## 5. 컴포넌트 상세

### 5.1 Sources (`models/staging/_sources.yml`)
dbt-duckdb external source로 5개 CSV를 raw로 선언. 실제 Kaggle 파일명 기준:

| source 테이블 | 파일 | 핵심 컬럼(키) |
|---|---|---|
| `orders` | `olist_orders_dataset.csv` | order_id(PK), customer_id(FK), order_status, order_purchase_timestamp |
| `order_items` | `olist_order_items_dataset.csv` | order_id+order_item_id(PK), product_id(FK), seller_id, price, freight_value |
| `products` | `olist_products_dataset.csv` | product_id(PK), product_category_name |
| `payments` | `olist_order_payments_dataset.csv` | order_id+payment_sequential(PK), payment_type, payment_value |
| `customers` | `olist_customers_dataset.csv` | customer_id(PK), customer_unique_id, customer_state |

- `product_category_name_translation.csv`는 카테고리 영문명 룩업(소형 정적) → **seed로 적재**(seed vs source 대비 학습 보너스).
- (선택) freshness: Olist엔 적재시각 컬럼이 없어 `order_purchase_timestamp`로 데모하되, 정적 데이터라 항상 stale → **freshness는 "개념 확인" 수준**으로만.

### 5.2 Staging (view, raw 1:1)
컬럼명 표준화·타입 캐스팅·정리만. `{{ source('olist', ...) }}` 참조.
- `stg_orders` · `stg_order_items` · `stg_products` · `stg_payments` · `stg_customers`

### 5.3 Intermediate
- `int_order_items_enriched` — **grain: order_item**. `stg_order_items` + `stg_products`(영문 카테고리, seed 룩업) 조인. 파생: 아이템 금액 = price + freight_value.

### 5.4 Marts
| 모델 | grain | 내용 |
|---|---|---|
| `fct_orders` | 주문 1행 | int_order_items_enriched를 주문단위 집계(items_count, gross_item_value, freight) + stg_orders(status·날짜·customer) + 결제합(stg_payments 집계) |
| `fct_daily_sales` | 구매일자 | fct_orders를 `order_purchase_date`로 집계(orders_count, total_payment, distinct_customers) |
| `dim_customers` | customer_id | stg_customers. ⚠️ Olist는 customer_id가 주문마다 1개(customer_unique_id가 실인물) → 이 quirk를 노트에 기록 |
| `dim_products` | product_id | stg_products + 카테고리 영문명(seed 조인) |

## 6. 테스트

- **Generic 4종**(신문법 `arguments:` 래퍼):
  - `unique`+`not_null`: 각 PK
  - `relationships`: `stg_order_items.order_id` → `stg_orders.order_id`
  - `accepted_values`: `order_status` ∈ {delivered, shipped, canceled, unavailable, invoiced, processing, created, approved}
- **Singular 1종**(`tests/`): 결제 정합성 — `fct_orders`에서 `payment_value < 0` 또는 (아이템 있는데 결제 0)인 행이 있으면 실패.
- **SKIP 게이트 재현**: 일부러 테스트 하나를 깨서 `dbt build`에서 **상위 실패 → 하위 SKIP** 관찰(jaffle 미재현분).

## 7. Snapshots (SCD2) — 정적 데이터 난점 해결

Olist external CSV는 읽기 전용·정적이라 그냥은 SCD2가 안 보임 → **통제된 변경 실습**:

1. `orders`를 **변경 가능한 raw 테이블**로 DuckDB에 적재(별도 테이블).
2. `snapshots/orders_snapshot` — strategy=`check`, `check_cols: [order_status]`, unique_key=`order_id`. **1차 `dbt snapshot`**.
3. 한 주문의 `order_status`를 `UPDATE`(예: shipped→delivered).
4. **2차 `dbt snapshot`** → 기존 행 `dbt_valid_to` 채워지고 **새 행 생성**, `dbt_valid_from/to` 변화를 직접 관찰(이론 5.4 검증).

## 8. 문서·계보 & 로그

- `dbt docs generate` → **source→stg→int→mart** lineage DAG · node_color(bronze=seed/source, silver=staging, gold=marts) 확인(이론 8장).
- `dbt-poc/실습로그.md`에 **STEP 4~** 이어쓰기(쳐본 명령/관찰/정오표).
- `dbt (이론).md`의 "미검증" 꼬리표 제거: source/freshness(5.2), intermediate(9.x), singular(5.5), SCD2(5.4), SKIP 게이트(7.1).

## 9. 라이선스 & 레포

- Olist = **CC BY-NC 4.0**(비상업). 학습/POC OK, 제품화 X.
- 원본 CSV(`dbt-poc/olist/data/`)·`*.duckdb`는 **`.gitignore`로 제외**(45MB + 재배포 주의). 다운로드 절차는 `dbt-poc/olist/README.md`에 기록.
- 코드는 기존 private 레포 **`10000JI/dbt-study`**의 `dbt-poc/olist/`로 커밋.

## 10. Phase 2 (확장, 향후)

`sellers`/`reviews`/`geolocation` 추가 → `dim_sellers`, 리뷰 관련 마트, 추가 테스트. freshness 심화. *(본 설계 범위 밖, 별도 사이클)*

## 11. 가정 & 미해결

- **A1**: dbt-duckdb external source가 설치 버전에서 CSV 직접 참조를 지원한다(셋업 시 검증).
- **A2**: Python 3.13에 dbt 휠 설치 가능(불가 시 3.9 폴백).
- **A3**: 사용자가 Kaggle에서 zip을 받아 지정 폴더에 둔다(취득 절차는 구현 계획에서 안내).
- **A4**: snapshot 변경 실습용 mutable orders 테이블 적재 방식의 정확한 구현은 plan에서 확정.
