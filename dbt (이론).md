# dbt (data build tool) — 이론

<!-- 데이터 엔지니어링 학습 노트. ELT 파이프라인에서 **변환(Transform)**을 담당하는 오픈소스 도구. -->
<!-- 모든 사실은 공식 문서(docs.getdbt.com), dbt-labs GitHub, dbt Labs 블로그/FAQ로 교차 검증함 (기준: 2026-06). -->

<!-- --- -->

## 1. dbt란?

- **정의**: 데이터 웨어하우스(DW) 안에 **이미 적재된 데이터를 SQL `SELECT` 문으로 변환**하는 커맨드라인 도구. 분석가/엔지니어가 작성한 SQL을 dbt가 컴파일하여 DW에서 실행하고, 그 결과를 **테이블/뷰로 물질화(materialize)** 한다.
- **핵심 기능**: 사용자는 비즈니스 로직(SQL `SELECT`)만 작성하면 되고, dbt가 **materialization, 트랜잭션, DDL, 스키마 변경**을 알아서 처리한다.
- **역할(ELT의 "T")**: dbt는 **ELT(Extract-Load-Transform)** 에서 **T(Transform)** 만 담당한다. 데이터를 추출(E)·적재(L)하지 않으며, "이미 웨어하우스에 적재된 데이터를 변환하는 데 매우 뛰어난" 도구다.
- **분석 엔지니어링(Analytics Engineering)**: dbt는 소프트웨어 엔지니어링의 모범 사례(**버전 관리, 테스트, 문서화, 모듈화, CI/CD**)를 데이터 변환 작업에 도입한다. 이 패러다임을 "analytics engineering"이라 부른다.
- **라이선스**: **dbt Core는 Apache License 2.0** (2016년 최초 릴리스부터). dbt Cloud / dbt Server는 별도의 더 제한적인 라이선스 (→ 13장).

> **dbt는 "쿼리 엔진"이 아니다**: dbt는 자체 실행 엔진이 없다. Snowflake·BigQuery·Redshift·Databricks·Spark 같은 **기존 DW/엔진에 SQL을 컴파일해 떠넘기는(push-down) 변환 오케스트레이터**다. 즉 연산은 연결된 DW가 수행하고, dbt는 변환 로직의 **구조·의존성·테스트·문서**를 관리한다.

**데이터 스택에서 dbt의 위치 (공식 개요도):**

![dbt가 클라우드 데이터 플랫폼에서 수집·변환·시각화 도구와 함께 동작하는 위치를 나타낸 개요도](https://docs.getdbt.com/img/docs/platform-overview.jpg?v=2)

> 출처: dbt 공식 문서 — https://docs.getdbt.com/docs/introduction
> 데이터 소스 → (수집/적재) → **클라우드 데이터 플랫폼 안에서 dbt가 변환(T) 담당** → BI/시각화로 이어지는 흐름을 보여준다.

---

## 2. 등장 배경

### 2.1 ETL → ELT 패러다임 전환

- 전통적 **ETL**: 데이터를 추출(E) → 별도 서버에서 변환(T) → DW에 적재(L). 변환 로직이 DW 밖(전용 ETL 도구)에 존재.
- 클라우드 DW(Snowflake, BigQuery, Redshift)의 등장으로 **저장·연산이 저렴하고 강력**해지면서, "먼저 원본을 그대로 적재(EL)하고, **DW 내부에서 SQL로 변환(T)**" 하는 **ELT**가 표준이 됨.
- 이때 "DW 안에서의 변환(T)"을 체계적으로 관리할 도구가 필요해졌고, 그 빈자리를 dbt가 채움.

### 2.2 분석가가 마주한 문제

- 변환 로직이 **여기저기 흩어진 SQL 스크립트**로 존재 → 의존성 관리 불가, 재현 불가, 테스트 없음, 문서 없음.
- 분석가는 **SQL은 능숙하지만 소프트웨어 엔지니어링(버전관리/테스트/CI)에는 익숙하지 않음** → "SQL 사용자"와 "엔지니어링 규율" 사이의 간극.

### 2.3 dbt의 탄생

- **Fishtown Analytics**(이후 사명 변경 → **dbt Labs**)가 개발. 공동창업자 **Tristan Handy**가 초기 개념을 정립.
- 핵심 아이디어: *"분석가가 `SELECT` 문만 쓰면, dbt가 그것을 소프트웨어 엔지니어링 산출물(버전관리되고, 테스트되고, 문서화되고, 의존성이 관리되는 데이터 모델)로 바꿔준다."*
- **2016년** dbt Core 최초 릴리스 (Apache 2.0 오픈소스).

---

## 3. 핵심 개념 & 설계 철학

### 3.1 SQL `SELECT` = 데이터 모델

- dbt의 기본 단위는 **모델(model)** 이며, 고전적으로 **하나의 `SELECT` 문**이다(파일당 1모델).
- 사용자는 `CREATE TABLE`/`CREATE VIEW`/`INSERT` 같은 **DDL/DML을 직접 쓰지 않는다**. `SELECT`만 작성하면 dbt가 materialization 설정에 따라 DDL을 생성한다.
- *(보강)* dbt 1.3(2022)부터는 **Python 모델**(DataFrame을 반환)도 지원하므로, "모델 = 단일 SELECT"는 **대표적인 경우**이지 유일한 형태는 아니다.

### 3.2 소프트웨어 엔지니어링 모범사례의 도입

| 영역 | dbt가 제공하는 것 |
| --- | --- |
| 버전 관리 | 모델이 `.sql` 파일 → Git으로 관리 |
| 모듈화 | `ref()`로 모델을 조합, 매크로로 로직 재사용 |
| 테스트 | 데이터 테스트(unique/not_null 등)로 데이터 품질 단언 |
| 문서화 | description + 자동 생성 문서 사이트 + lineage 그래프 |
| 의존성 관리 | `ref()` 기반 **DAG** 자동 구성, 실행 순서 자동 결정 |

### 3.3 DAG 기반 의존성 (vs 수동 순서 관리)

- 모델 간 참조를 `ref()`로 표현하면 dbt가 **DAG(Directed Acyclic Graph)** 를 자동 구성하고 **실행 순서를 스스로 결정**한다. 사용자가 "A를 만든 뒤 B"를 수동으로 지정할 필요가 없다.

### 3.4 push-down 아키텍처 (자체 엔진 없음)

- dbt는 **연산을 수행하지 않는다**. 컴파일된 SQL을 **타깃 DW에 전송**해 DW의 연산 자원으로 실행한다. 따라서 성능·확장성은 **연결된 DW(Snowflake/BigQuery 등)에 종속**된다.

---

## 4. 아키텍처

### 4.1 핵심 2-컴포넌트: Compiler + Runner

dbt의 동작은 본질적으로 두 단계다 (Tristan Handy의 정의):

1. **Compiler (컴파일러)**: Jinja + SQL로 작성된 모델을 **순수 실행 가능 SQL**로 컴파일한다. `ref()`/`source()`를 실제 `database.schema.table` 식별자로 치환하고, Jinja 제어문/매크로를 전개한다. 결과는 `target/` 디렉토리에 기록됨.
2. **Runner (러너)**: 컴파일된 SQL을 DAG 순서대로 DW에 실행하여 테이블/뷰를 생성한다.

### 4.2 Adapter (어댑터) — DW 연결 계층

- dbt는 각 데이터 플랫폼마다 **전용 어댑터 플러그인**을 통해 연결한다. 어댑터는 dbt Core가 설치 시 자동 발견하는 **Python 모듈**이다.
- 어댑터가 플랫폼별 SQL 방언(dialect)·연결·DDL 차이를 흡수하므로, 동일한 dbt 프로젝트를 여러 DW에 (어느 정도) 이식할 수 있다.
- 종류: **Trusted Adapters**(dbt Labs의 신뢰 프로그램 충족) vs **Community Adapters**(커뮤니티 유지).
![alt text](image.png)

> 이번 실습 프로젝트(`jaffle_shop_duckdb`)는 **dbt-duckdb** 어댑터를 쓴다 — 별도 DW 서버 없이 로컬 파일(`jaffle_shop.duckdb`) 하나로 동작해 설치·실행이 가볍다. (튜토리얼에서 흔히 보이는 `dbt-postgres`와 달리 DB 서버 기동이 필요 없다.)


### 4.3 Jinja 템플릿팅 — "SQL을 위한 프로그래밍 환경"

- dbt는 **SQL + Jinja 템플릿 언어**를 결합한다. 공식 문서: *"Jinja를 쓰면 dbt 프로젝트가 SQL을 위한 프로그래밍 환경이 되어, 일반 SQL로는 불가능한 일을 할 수 있다."*
- Jinja로 가능한 것: **제어 구조(for/if), 환경 변수, 재사용 가능한 매크로(함수)**.
- 컴파일 시 Jinja가 전개되어 **순수 SQL**이 된다. 예: `for` 루프 → 결제수단별 `sum(case ... end)` 한 줄씩 생성.

### 4.4 컴파일에는 DW 연결이 필요

- `dbt compile`은 모든 모델의 SQL을 준비하기 위해 **데이터 플랫폼 연결이 필요**하다(introspective 쿼리로 메타데이터 수집). 컴파일 결과는 `target/` 디렉토리에 저장.
- *(보강)* `dbt parse`는 연결 없이 프로젝트 유효성만 검증 가능. `--no-introspect` 등의 플래그도 존재.

---

## 5. 구성요소 상세 (빌딩 블록)

dbt 프로젝트는 다음 리소스들로 구성된다.

> 🔬 **실습 검증 표기 안내**: 아래 `🔬 실습 검증` 인용블록은 1차 핸즈온에서 **직접 확인한 사실**이다(이론=공식 문서 기반과 구분).
> 환경: `jaffle_shop_duckdb` · dbt-core **1.10.22** + dbt-duckdb(duckdb 1.10.0) · macOS/Python 3.9.6 · 2026-06-11. 결과: `dbt build` **PASS=28**.
> (Python 3.9 캡으로 dbt가 1.10.x 고정 → jaffle 레포가 dbt≥1.11을 요구해 매 명령에 `--no-version-check` 필요)

### 5.1 Models (모델)

- **정의**: 변환을 표현한 `SELECT` 문(`.sql` 파일). 빌드 시 view/table 등으로 물질화됨.
- **참조**: 다른 모델은 반드시 `{{ ref('model_name') }}` 로 참조 → DAG 의존성 생성.
- 예: `select * from {{ ref('stg_customers') }}`

### 5.2 Sources (소스) — `source()`

- **정의**: EL 단계에서 적재된 **원본(raw) 테이블**을 추상화. 모델은 raw 테이블을 직접 쓰지 않고 `source()`로 참조해 lineage를 만든다.
- **문법**: `{{ source('source_name', 'table_name') }}` → 컴파일 시 `raw.jaffle_shop.orders` 등으로 치환.
- **YAML 정의** (`_sources.yml`):
```yaml
version: 2
sources:
  - name: jaffle_shop
    database: raw
    schema: jaffle_shop        # name과 다를 때만 명시
    tables:
      - name: orders
        identifier: api_orders # 실제 테이블명이 다를 때
      - name: customers
```
- **Source Freshness(소스 신선도)**: 원본이 기대대로 갱신되는지 추적. `loaded_at_field`(적재 시각 컬럼)와 임계값으로 설정하고 `dbt source freshness`로 검사.
```yaml
config:
  freshness:
    warn_after:  {count: 12, period: hour}
    error_after: {count: 24, period: hour}
  loaded_at_field: _etl_loaded_at
```
  - `warn_after`(경고)/`error_after`(에러)/`freshness: null`(검사 제외).
  - 신선해진 소스의 하위만 빌드: `dbt build --select "source_status:fresher+"`

> 🔬 **실습 검증**: jaffle 데모는 `source()`를 **쓰지 않는다** — 원본을 seeds(CSV)로 적재하고 staging이 `{{ ref('raw_customers') }}`로 직접 참조한다. (`stg_customers.sql` 주석: *"Normally we would select from the table here, but we are using seeds to load our data in this project"*) 따라서 `source()`·freshness는 1차(jaffle)에선 미검증.
> → ✅ **Olist 본편 검증(2026-06-18)**: `source()`를 dbt-duckdb **external source**로 직접 실검증. `_sources.yml`에 `meta.external_location: read_csv_auto('data/olist_{name}_dataset.csv')` 선언 → `{name}`이 테이블명으로 치환되어 raw CSV를 `{{ source('olist','orders') }}`로 **seed 없이 직접 참조**. (freshness는 Olist에 적재시각 컬럼이 없어 개념 확인 수준 — 정적 데이터라 항상 stale.)

#### 5.2.1 `source()` vs `ref()` — "데이터가 어디서 왔는가"

두 함수 모두 **의존성(DAG)** 을 만든다는 점은 같다. 차이는 **가리키는 대상이 dbt 안에서 만들어진 것인지, 밖에서 적재된 것인지**다.

| 구분 | **`source()`** | **`ref()`** |
| --- | --- | --- |
| 가리키는 대상 | dbt **밖에서** EL 도구(Fivetran/Airbyte 등)가 적재한 **raw 테이블** | dbt가 **직접 만든** 모델 또는 seed |
| 데이터 출처 | 운영 DB·외부 적재 파이프라인(이미 존재한다는 전제) | `seeds/*.csv`(`dbt seed`) 또는 상위 모델 |
| YAML 정의 | **`sources:` 블록 필수**(`_sources.yml`) | 불필요(`.sql`/`.csv` 파일만 있으면 됨) |
| freshness 검사 | `dbt source freshness`로 **원본 갱신 지연 추적 가능** | 불가(dbt가 만든 것이라 개념상 무의미) |
| lineage 위치 | 그래프의 **최상류 source 노드**(보통 초록색) | source/seed **하류**의 모델 노드 |
| 컴파일 결과(예) | `"raw"."jaffle_shop"."customers"` | `"jaffle_shop"."main"."raw_customers"` |

**같은 `stg_customers`를 두 방식으로 쓰면:**

```sql
-- (A) 지금 jaffle 방식 — seed를 ref()로 참조
select * from {{ ref('raw_customers') }}
-- 컴파일 → select * from "jaffle_shop"."main"."raw_customers"

-- (B) source() 방식 — 외부 raw 테이블을 참조 (별도 YAML 선언 필요)
select * from {{ source('jaffle_shop', 'customers') }}
-- 컴파일 → select * from "raw"."jaffle_shop"."customers"
```

(B)를 쓰려면 먼저 source를 선언해야 한다:
```yaml
# models/staging/_sources.yml
version: 2
sources:
  - name: jaffle_shop
    database: raw          # 외부에 이미 존재하는 raw DB/스키마
    tables:
      - name: customers
```

**왜 jaffle은 `source()` 대신 seed를 쓰나?** → `source()`는 *"누군가 이미 raw 테이블을 적재해 두었다"* 는 **외부 전제**가 필요하다. 학습용 레포는 그 전제를 만들 수 없으므로, CSV를 함께 넣고 `dbt seed`로 자급자족한다. 즉 **seed가 source의 대역(代役)** 이다. 실무 표준 흐름은 **`source()`(raw) → staging(`ref`) → marts(`ref`)** 이며, jaffle은 맨 앞 `source()`만 seed로 대체했을 뿐 나머지 구조는 동일하다.

### 5.3 Seeds (시드)

- **정의**: dbt 프로젝트 내 **CSV 파일**을 `dbt seed`로 DW에 테이블로 적재. 버전 관리·리뷰가 가능해 **변경이 드문 정적 데이터**에 적합(국가코드 매핑, 코드 룩업 등).
- 위치: `seeds/` 디렉토리. 참조: 모델처럼 `{{ ref('country_codes') }}`.
- **부적합**: 대용량 raw 데이터, PII/비밀번호 등 민감 운영 데이터.

> 🔬 **실습 검증**: `dbt seed`(build에 포함)로 `raw_customers`(100행)·`raw_orders`(99행)·`raw_payments`(113행)가 DuckDB에 **실테이블**로 적재됨. `show tables`에 `raw_*`가 그대로 보이고, `stg_*`(view)가 이 seed를 `ref()`로 참조. → jaffle에선 seed가 "원본 소스" 역할을 대신한다.

### 5.4 Snapshots (스냅샷) — SCD Type 2

- **정의**: 변경 가능한 원본 테이블의 변경 이력을 **Type 2 Slowly Changing Dimension(SCD2)** 으로 기록 → 과거 시점 상태 추적.
- **추가 메타 컬럼**:

| 컬럼 | 의미 |
| --- | --- |
| `dbt_valid_from` | 행이 유효해진 시점 |
| `dbt_valid_to` | 유효성이 끝난 시점 (현재 행은 기본 `NULL`) |
| `dbt_scd_id` | 스냅샷 행 고유 ID |
| `dbt_updated_at` | 원본 updated_at |

- **두 가지 전략**:
  - **timestamp(권장)**: `updated_at` 컬럼으로 변경 감지. 한 컬럼만 추적 → 스키마 변경에 강함.
  - **check**: 지정한 `check_cols`의 값 변화를 비교.
- **YAML 정의(dbt 1.9+ 표준)**:
```yaml
snapshots:
  - name: orders_snapshot
    relation: ref('stg_orders')
    config:
      schema: snapshots
      unique_key: order_id
      strategy: timestamp
      updated_at: updated_at
      dbt_valid_to_current: '9999-12-31'  # 1.9+: NULL 대신 특정값
      hard_deletes: 'new_record'          # 1.9+: 삭제 추적
```
- 명령: `dbt snapshot`. `unique_key`는 반드시 유일해야 함(uniqueness 테스트 권장).
- *(버전 주의)* 레거시는 `.sql` 파일 내 `{% snapshot %} ... {% endsnapshot %}` 블록 방식이었으나, 최신 docs는 위 YAML 방식으로 대체됨.

> 🔬 **실습 검증**: jaffle엔 snapshot 없어 1차 미검증.
> → ✅ **Olist 본편 검증(2026-06-18)**: `snap_orders_src`(shipped 200건 mutable table)에 `strategy: check, check_cols: [order_status]` 스냅샷. 1차 snapshot 후 한 주문 status를 `UPDATE shipped→delivered` → 2차 snapshot에서 **그 주문이 2행**으로: 옛 행(shipped, `dbt_valid_to` 채워짐) + 새 행(delivered, `dbt_valid_to` NULL=현재). 총 200→201행. `dbt_valid_from/to` 이력 추적 실확인. (정적 CSV는 mutable 테이블을 만들어 직접 변경해야 SCD2가 관찰됨.)

### 5.5 Data Tests (데이터 테스트)

- **정의**: 모델·소스·시드·스냅샷에 대한 **단언(assertion)**. `dbt test` 실행 시 테스트 SQL이 **0개의 실패 행(failing rows)** 을 반환하면 통과.
- **두 종류**:
  - **Singular test(단수 테스트)**: `tests/` 디렉토리의 `.sql` 파일에 작성한 일회성 SQL 쿼리.
  - **Generic test(제네릭 테스트)**: 인자를 받는 **파라미터화된 쿼리**(매크로처럼 `test` 블록으로 정의), YAML에서 재사용.
- **내장 제네릭 테스트 4종**: `unique`, `not_null`, `accepted_values`, `relationships`.
- YAML 설정 예:
```yaml
columns:
  - name: customer_id
    data_tests:
      - unique
      - not_null
  - name: status
    data_tests:
      - accepted_values: { values: ['active', 'churned'] }
```
- *(버전 주의)* 구버전은 `tests:` 키, 최신은 명확성을 위해 **`data_tests:`** 를 선호(둘 다 지원).

> 🔬 **실습 검증 & 정오표**: jaffle build에서 4종 제네릭 테스트가 모두 등장(`unique`·`not_null`·`accepted_values`·`relationships`, 20개 전부 PASS). 단 **현행 jaffle(dbt 1.11 요구)의 실제 `schema.yml` 문법이 위 예제와 다르다**:
> 1. 키로 `data_tests:`가 아니라 **`tests:`** 를 쓴다(둘 다 유효).
> 2. 인자 있는 테스트(`accepted_values`·`relationships`)는 인자를 **`arguments:` 블록으로 감싼다**(신문법). 본문의 `accepted_values: { values: [...] }` **플랫 문법은 구문법**:
> ```yaml
> # 현행 jaffle 실제 문법
> - name: status
>   tests:
>     - accepted_values:
>         arguments:
>           values: ['placed','shipped','completed','return_pending','returned']
> - name: customer_id
>   tests:
>     - relationships:
>         arguments:
>           to: ref('customers')
>           field: customer_id
> ```
> `unique`/`not_null`처럼 인자 없는 테스트는 종전과 동일(`- unique` 한 줄). → 최신 레포 예제를 볼 땐 `arguments:` 래퍼 유무에 주의.

### 5.6 Macros (매크로)

- **정의**: 재사용 가능한 **Jinja 코드 조각**(다른 언어의 함수에 해당). `.sql` 파일에 작성하며 보통 `macros/` 디렉토리에 둔다.
- **용도**: 반복 SQL 로직 추출(DRY), 패키지(dbt_utils 등) 활용.

### 5.7 Materializations (물질화 전략)

- **정의**: 모델을 DW에 **영속화하는 전략**. 내장 5종:

| 전략 | 동작 |
| --- | --- |
| **view** (기본값) | `create view as`로 매번 재생성. 저장X, 항상 최신 |
| **table** | `create table as`로 물리 테이블 생성. 빠른 조회, 데이터는 스냅샷 시점 |
| **incremental** | 변경분만 insert/update (대용량·증분 적재) |
| **ephemeral** | DB에 생성되지 않고, 참조하는 모델에 **CTE로 인라인** |
| **materialized view** | 테이블의 조회 성능 + 뷰의 신선도를 결합 |

- 설정: `{{ config(materialized='table') }}` 또는 `dbt_project.yml`. **커스텀 materialization**도 정의 가능.

> 🔬 **실습 검증**: `dbt_project.yml`의 폴더별 기본값(`staging: +materialized: view`, 루트 `+materialized: table`)대로 `stg_*`는 **view**, `customers`/`orders`는 **table**로 생성됨을 `show tables`로 확인. **동일한 SELECT라도 materialization이 물리 객체 종류를 바꾼다**가 핵심. `incremental`·`ephemeral`·`materialized view`는 1차 미검증(대용량/증분은 Track B 또는 별도 실습).

### 5.8 `ref()` & DAG / Lineage

- `ref('model')`: 모델 간 의존성을 만들고 **DAG**를 구성 → dbt가 실행 순서를 자동 결정.
- `source('src','tbl')`: 원본 테이블 의존성을 만듦.
- 이 둘이 모여 **전체 데이터 계보(lineage)** 그래프를 형성.

> 🔬 **실습 검증**: `{{ ref('stg_customers') }}` → 컴파일본에서 **`"jaffle_shop"."main"."stg_customers"`** 로 치환됨을 `target/compiled/.../customers.sql`에서 원본과 대조 확인. 즉 `database.schema.table`를 **큰따옴표로 감싼 3단 완전수식**(DuckDB 어댑터 기준). 하드코딩이 아니라 `ref()`를 쓰기 때문에 dbt가 의존을 추적해 DAG(`raw→stg→마트`)와 실행 순서를 자동 도출(→ 8장 lineage 캡처).

---

## 6. 프로젝트 구조 & 설정 파일

### 6.1 `dbt_project.yml` — 프로젝트 설정 (필수)

- 디렉토리가 dbt 프로젝트임을 선언하고 동작·리소스 위치를 지정.
- 주요 키:
  - 식별: `name`, `version`, `profile`(profiles.yml의 프로필명과 매칭), `config-version: 2`
  - 경로: `model-paths`, `seed-paths`, `snapshot-paths`, `macro-paths`, `analysis-paths`, `test-paths`, `clean-targets` …
  - 리소스 설정: `models:`, `seeds:`, `snapshots:`, `sources:`
  - 훅: `on-run-start`, `on-run-end`
- **문법 규칙**: 이 파일에서는 다중 단어 키에 **대시**(`model-paths`), 다른 YAML에서는 **언더스코어**. config는 폴더명과 구분하려 **`+` 접두사**(`+materialized: table`).

> 🔬 **실습 검증**: jaffle `dbt_project.yml` 실측 — `name: jaffle_shop` ↔ `profile: jaffle_shop`이 **동일 문자열로 매칭**(이게 `profiles.yml`의 최상위 키와 연결됨). `config-version: 2`, `version: '0.1'`. 경로 키는 전부 **대시**(`model-paths`/`seed-paths`/`test-paths`), config는 **`+` 접두사**(`+materialized`, `+docs`)로 실제 작성됨 → 본문 문법 규칙 그대로 확인. 단 `require-dbt-version: [">=1.11.0", "<2.0.0"]`가 박혀 있어 **1차 환경(dbt-core 1.10.22)은 이 제약을 못 만족** → 매 명령에 `--no-version-check`를 붙여 우회함(5장 환경 주석과 동일 원인).

### 6.2 `profiles.yml` — 연결 자격증명

- 타깃 DW **연결 정보(자격증명)** 저장. 민감정보를 프로젝트/버전관리 밖에 둔다.
- 위치(권장): `~/.dbt/profiles.yml` (탐색 순서: `--profiles-dir` → 프로젝트 루트 → `~/.dbt/`).
- 핵심 개념: **Profile**(명명된 연결 묶음) → **Target**(dev/prod 등 환경) → **outputs**(실제 연결값).
```yaml
my_project_profile:
  target: dev
  outputs:
    dev:
      type: snowflake          # 어댑터 타입(필수)
      account: abc123
      database: docs_team
      schema: dev_schema
      user: username
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"  # 환경변수 권장
      warehouse: warehouse
      threads: 4
    prod:
      type: snowflake
      schema: analytics
      threads: 4
```
- target 전환: `dbt run --target prod`

> 🔬 **실습 검증**: jaffle `profiles.yml` 실측 — 본문 Snowflake 예제와 달리 **자격증명이 사실상 0개**다. DuckDB는 로컬 파일 기반이라 `account`/`user`/`password`/`warehouse`가 전부 불필요하고, 필요한 건 **파일 경로 하나**뿐:
> ```yaml
> jaffle_shop:            # ← dbt_project.yml의 profile: 값과 일치해야 함
>   target: dev
>   outputs:
>     dev:
>       type: duckdb
>       path: 'jaffle_shop.duckdb'   # 이 파일이 곧 DW
>       threads: 24
> ```
> 위치도 권장값 `~/.dbt/`가 아니라 **프로젝트 루트**에 둠 → 탐색 순서(`--profiles-dir` → 프로젝트 루트 → `~/.dbt/`)상 **루트 파일이 먼저 채택**됨을 확인. **Profile(`jaffle_shop`) → Target(`dev`) → outputs** 3단 구조와 "profile 키 ↔ dbt_project.yml의 profile 매칭"도 그대로 성립.

### 6.3 표준 디렉토리

`models/`, `seeds/`, `snapshots/`, `tests/`, `macros/`, `analyses/`, `docs/`, `dbt_packages/`(패키지 설치 경로) 등 — 각각 `dbt_project.yml`의 `*-paths` 키에 대응.

> 🔬 **실습 검증**: jaffle에 **실제 존재하는 폴더는 `models/`·`seeds/`만**(+ 빌드 산출물 `target/`·`logs/`, 데모용 `etc/`·`images/`). 흥미로운 점은 `dbt_project.yml`이 `macro-paths: ["macros"]`·`analysis-paths: ["analysis"]`·`test-paths: ["tests"]`를 **선언하지만 해당 폴더는 물리적으로 없다**는 것 → **dbt는 선언된 선택적 경로가 비어 있어도 무시하고 진행**(빌드 PASS). `snapshots/`·`macros/`·`packages.yml`·`dbt_packages/`도 없음 → 이번 실습은 **스냅샷·커스텀 매크로·외부 패키지를 쓰지 않는 최소 구성**임을 방증. 즉 "표준 디렉토리 = 항상 다 있는 것"이 아니라 **쓰는 리소스만큼만 존재**한다.

### 6.4 Properties YAML (`schema.yml`)

- **Properties(설명)** vs **Configs(빌드 방식)** 를 구분:
  - **Properties**: 리소스 **설명**(`description`), 데이터 테스트, exposures 등.
  - **Configs**: **어떻게 빌드할지**(materialization, schema, tags, meta). 계층적 상속/오버라이드.
```yaml
version: 2
models:
  - name: customers
    description: "Customer dimension table"
    config:
      materialized: table
      tags: [pii]
    columns:
      - name: customer_id
        description: "Unique customer identifier"
        data_tests: [unique, not_null]
```

---

## 7. 실행 명령어

| 명령 | 설명 |
| --- | --- |
| `dbt run` | 모델 실행(물질화) |
| `dbt test` | 데이터 테스트 실행 |
| `dbt seed` | CSV 시드를 DW에 적재 |
| `dbt snapshot` | 스냅샷 실행 |
| `dbt build` | 모델·시드·스냅샷·테스트를 **DAG 순서로 통합 실행** |
| `dbt compile` | SQL만 컴파일(`target/`에 기록), 실행 안 함 |
| `dbt docs generate` / `serve` | 문서 카탈로그 생성 / 로컬 호스팅 |
| `dbt source freshness` | 소스 신선도 검사 |
| `dbt deps` | `packages.yml`의 패키지 설치 |
| `dbt debug` / `dbt list(ls)` | 연결 진단 / 리소스 목록 |

### 7.1 `dbt build`의 오케스트레이션 순서 (핵심)

- `dbt build`는 **모델·테스트·스냅샷·시드**를 **DAG(의존성) 순서**로 묶어 실행한다.
- 핵심 규칙: **상위 리소스의 테스트가 실패하면 하위 리소스는 SKIP**된다.
  > 예: `model_b`가 `model_a`에 의존하고, `model_a`의 `unique` 테스트가 실패하면 → `model_b`는 SKIP.
- 즉 각 노드를 빌드하면서 그 노드의 테스트가 **게이트** 역할을 하여, 통과해야 하위로 진행. 단일 manifest/run_results 산출.

> 🔬 **실습 검증**: jaffle `dbt build` → `3 seeds, 3 view models, 2 table models, 20 data tests`를 한 DAG로 실행, **PASS=28 WARN=0 ERROR=0 SKIP=0**(0.93s). 관찰된 실행 순서: `seed 적재 → stg_*(view) → stg 테스트 → customers/orders(table) → 마트 테스트`. 단 jaffle은 전부 PASS라 상위 실패→하위 SKIP 게이트는 1차 미재현.
> → ✅ **Olist 본편 재현(2026-06-18)**: `_staging.yml`에서 order_status accepted_values의 `'delivered'`를 임시 제거 → `dbt build -s stg_orders+`에서 **stg_orders 테스트 FAIL**(`Got 1 result`) → 하위 `fct_orders`·`fct_daily_sales`(+그 테스트) **SKIP** (`PASS=7 ERROR=1 SKIP=9`). 트리거는 모델 빌드 실패가 아니라 **상위 노드의 테스트 실패**임을 확인. (단 `int_order_items_enriched`는 stg_orders의 하위가 아니라 SKIP 대상 아님 — DAG 의존을 정확히 봐야 SKIP 범위를 안다.)

### 7.2 노드 선택 문법 (`--select`, 그래프 연산자)

```bash
dbt run --select "my_model"                 # 단일
dbt run --select "path:marts/finance"       # 경로
dbt run --select "tag:nightly"              # 태그
dbt run --select "config.materialized:table"
```
- **그래프 연산자**: `my_model+`(자신+하위), `+my_model`(상위+자신), `+my_model+`(상하위 전부), `@my_model`(가장 포괄), `*`(와일드카드).
- **집합 연산자**: 쉼표 `,` = 교집합(AND), 공백 = 합집합(OR).
- **선택 메서드**: `tag:`, `path:`, `config:`, `source:`, `source_status:`, `state:`(예: `state:modified+`, `--state` 필요), `result:`, `test_type:` 등.

> 🔬 **실습 검증**: 1차에서 **실제로 실행해 본 명령**과 **미검증 명령**을 구분하면 —
>
> | 명령 | 1차 검증 | 관찰 결과 |
> | --- | --- | --- |
> | `dbt seed` | ✅ | `raw_*` 3종 적재(`dbt build`에 포함되어 실행) |
> | `dbt build` | ✅ | 한 DAG로 통합 실행, **PASS=28**(0.93s) |
> | `dbt compile` | ✅ | `target/compiled/...`에 순수 SQL 생성, `ref()` 치환 확인 |
> | `dbt docs generate`/`serve` | ✅ | `catalog.json` + lineage DAG(→ 8장) |
> | `dbt snapshot` | ❌ | 스냅샷 리소스 없음 → 미실행 |
> | `dbt source freshness` | ❌ | source 정의 없음(seed 구조) → 적용 불가 |
> | `dbt deps` | ❌ | `packages.yml` 없음 → 설치할 패키지 없음 |
> | `--select` 그래프/집합 연산자 | ❌ | 전체 빌드만 수행, **노드 선택 문법은 1차 미검증** |
>
> 모든 명령에 `--no-version-check`를 동반(환경: dbt-core **1.10.22** + dbt-duckdb).
> → ✅ **Olist 본편 추가 검증(2026-06-18, dbt 1.11 신환경)**: `dbt snapshot`(SCD2), `dbt show --inline`(임의 쿼리), source() 적재까지 실행. 남은 ❌: `dbt source freshness`(Olist에 적재시각 없음), `dbt deps`(패키지 미사용), `--select` 그래프 연산자는 SKIP 게이트 재현 때 `stg_orders+`로 **일부 사용**(하위 선택 확인). 완전한 노드 선택 문법은 추후.

---

## 8. 문서화 & Lineage

- `dbt docs generate`: 모델 코드, 테스트, 메타데이터 + DW information schema(컬럼 타입/테이블 크기) + 사용자 description을 모아 **카탈로그**와 **정적 문서 사이트**, **DAG lineage 그래프**를 생성.
- `dbt docs serve`: 생성된 문서를 로컬에서 호스팅.
- description은 `schema.yml`에 작성하며, 긴 문서는 **docs block**으로 분리:
```jinja
{% docs table_events %}
This table contains clickstream events from the marketing website...
{% enddocs %}
```
```yaml
models:
  - name: events
    description: '{{ doc("table_events") }}'
```

> 🔬 **실습 검증**: `dbt docs generate` → `target/catalog.json` 생성 후 `dbt docs serve`(localhost:8080)로 확인. 모델 상세에 컬럼 타입·설명·테스트·**Depends On / Referenced By**가 자동 표기되고, **lineage DAG**(`raw_* → stg_* → customers`)가 그려짐. 그래프 노드 색이 `dbt_project.yml`의 `node_color`(bronze=seed / silver=staging / gold=marts) 설정과 **정확히 일치**함을 캡처로 확인. (별도 학습노트 HTML에 캡처 보존)

---

## 9. 모범 사례 — 레이어링 (staging / intermediate / marts)

dbt Labs 공식 Best Practices 가이드는 프로젝트를 **3개 변환 레이어**로 구성하길 권장한다:

| 레이어 | 역할 | 네이밍 |
| --- | --- | --- |
| **Staging** | 소스 데이터로부터 만드는 **원자적(atomic) 빌딩 블록**(1:1 정리·표준화) | `stg_` |
| **Intermediate** | staging을 쌓아 엔티티로 결합하기 위한 **중간 로직**(조인·변환) | `int_` |
| **Marts** | 조직이 관심 갖는 **비즈니스 정합(business-conformed) 엔티티** | `fct_`(fact) / `dim_`(dimension) |

- 원칙: **source-conformed → business-conformed** 으로 점진적 변환.
- 추가: 반복 로직은 **macros**로 DRY, 핵심 컬럼에 테스트·문서 부여.
- *(주의)* 네이밍 접두사(`stg_/int_/fct_/dim_`)는 가이드·jaffle_shop 예제에서 널리 쓰이는 컨벤션.

> 🔬 **실습 검증**: jaffle는 **staging + marts 2계층만** 존재(intermediate 없음): `stg_*`(view) → `customers`/`orders`(table).
> → ✅ **Olist 본편 검증(2026-06-18)**: 3계층을 직접 작성 — **staging(view) 5종 → `int_order_items_enriched`(intermediate, view) → marts(table) 4종**(`dim_customers`/`dim_products`/`fct_orders`/`fct_daily_sales`). `int_`/`fct_`/`dim_` 네이밍, **generic(unique·not_null·relationships·accepted_values) + singular(`assert_fct_orders_amounts_non_negative`) 테스트** 모두 작성·PASS(`dbt build PASS=40`). intermediate가 마트 조인의 중간 빌딩블록으로 동작함을 확인(int를 fct_orders가 집계 참조).

### 9.1 "표준"의 정체 — 컨벤션 vs 엔진 규칙 (강제 아님)

위 레이어링·네이밍은 **dbt 엔진이 강제하는 문법 규칙이 아니라, dbt Labs가 공식 권장하는 관례(convention)** 다. 둘을 구분하면:

| 무엇이 정하나 | 강제성 | 예 |
| --- | --- | --- |
| **dbt 엔진 규칙** | 강제(O) — 어기면 동작 안 함 | `.sql`은 `models/`에, 참조는 `ref()`, materialization은 폴더/`config()` 설정으로 결정 |
| **레이어링·네이밍 컨벤션** | 권장(X) — 어겨도 동작함 | `stg_/int_/fct_/dim_` 접두사, raw 1:1 staging, 3계층 구조 |

- **핵심**: dbt는 `stg_`라는 **이름을 전혀 해석하지 않는다**. view가 되는 건 이름이 아니라 **`models/staging/` 폴더에 걸린 `+materialized: view`** 때문(→ 5.7·6.4 config 우선순위). 파일을 루트로 옮기면 이름이 `stg_`여도 table이 된다.
- 그럼에도 **사실상의 업계 표준**이라 대부분의 dbt 프로젝트가 이 구조를 따른다. 신규 합류자가 관례를 알면 프로젝트 구조를 즉시 파악할 수 있다는 게 컨벤션의 가치.

> **config 우선순위(같은 모델에 여러 설정이 겹칠 때)**: `파일 안 {{ config() }}` > 하위 폴더 설정 > 상위 폴더 설정 > 프로젝트 기본값. (가장 구체적인 설정이 이김) → `stg_*`가 view인 이유: 프로젝트 기본 `+materialized: table`을 `staging:` 폴더의 `+materialized: view`가 덮어쓰기 때문.

### 9.2 실무에서 staging 모델은 누가 만드나 — 직접 작성 + 자동 생성

jaffle의 `stg_*.sql`은 **튜토리얼이 미리 제공**한 것이고, **실무에선 분석 엔지니어가 직접 작성**한다. 표준 흐름:

```
EL 도구(Fivetran 등)가 raw 적재   ← 내 일 아님
   → source 선언(_sources.yml)     ← 내가 함
   → raw 1개당 stg_ 모델 1개 작성   ← 내가 함 (컬럼명 정리·캐스팅·표준화)
   → stg를 ref()로 쌓아 마트 작성    ← 내가 함
```

- **원칙: raw 테이블 1개 = staging 모델 1개(1:1)**. raw가 50개면 stg 파일도 50개.
- raw가 많을 때 손으로 다 짜지 않도록 **`dbt-codegen` 패키지**로 뼈대를 자동 생성한다:
  - `generate_source` → `_sources.yml` 초안 생성
  - `generate_base_model` → source 컬럼을 읽어 `stg_*` SQL 초안 출력 → 복사 후 정리만 손봄
- *(주의)* codegen은 **편의 도구**일 뿐 표준은 아니다. **진짜 표준은 "raw→stg 1:1 + 레이어 구조"**이며, 자동 생성 여부는 선택.

> 🔬 **실습 검증**: jaffle은 stg가 이미 제공됨 → "만들어진 걸 분석"(1차).
> → ✅ **Olist 본편 검증(2026-06-18)**: source 선언(`_sources.yml`)부터 stg 5종을 **직접 작성** — raw CSV 1개당 stg 모델 1개(1:1)로 컬럼명 표준화·타입 캐스팅. 실무 흐름(source→staging(ref)→marts(ref))을 손으로 재현. (codegen 자동 생성은 미사용 — 직접 작성으로 체득.)

---

## 10. 지원 데이터 플랫폼 (어댑터)

- dbt는 DW/레이크/쿼리엔진에 **어댑터 플러그인**(Python 모듈)으로 연결. **Trusted** vs **Community** 어댑터로 구분.
- 주요 **Trusted 어댑터**(dbt Labs 유지): **Snowflake, BigQuery, Redshift, Databricks, Postgres, Apache Spark, Starburst/Trino** 등. 그 외 ClickHouse, DuckDB, Oracle, Teradata 등 24+ 종.
- *(주의)* 일부 어댑터(Trino/Starburst 등)는 벤더가 함께 관여하므로 "dbt Labs 단독 유지"는 어댑터별로 다를 수 있음(문서 표기 기준).

---

## 11. 종합 예제

**소스 → staging 모델 → schema.yml**

```yaml
# models/staging/jaffle_shop/_sources.yml
version: 2
sources:
  - name: jaffle_shop
    database: raw
    schema: jaffle_shop
    config:
      freshness: { warn_after: {count: 12, period: hour} }
      loaded_at_field: _etl_loaded_at
    tables:
      - name: orders
      - name: customers
```

```sql
-- models/staging/jaffle_shop/stg_orders.sql
select
    id        as order_id,
    user_id   as customer_id,
    order_date,
    status
from {{ source('jaffle_shop', 'orders') }}
```

```sql
-- models/marts/dim_customers.sql
with customers as (
    select * from {{ ref('stg_customers') }}
),
orders as (
    select * from {{ ref('stg_orders') }}
)
select
    c.customer_id,
    c.first_name,
    count(o.order_id) as lifetime_orders
from customers c
left join orders o using (customer_id)
group by 1, 2
```

```yaml
# models/marts/_models.yml
version: 2
models:
  - name: dim_customers
    description: "Customer dimension table"
    columns:
      - name: customer_id
        description: "Unique customer identifier"
        data_tests: [unique, not_null]
```

**Jinja 매크로 + for 루프**
```sql
select
    order_id,
    {% for pm in ['credit_card', 'paypal', 'bank_transfer'] %}
    sum(case when payment_method = '{{ pm }}' then amount end) as {{ pm }}_amount
    {%- if not loop.last %},{% endif %}
    {% endfor %}
from {{ ref('stg_payments') }}
group by 1
```

---

## 12. dbt Core vs dbt Cloud

| 구분 | dbt Core | dbt Cloud |
| --- | --- | --- |
| 형태 | 오픈소스 CLI | 관리형 SaaS |
| 라이선스 | **Apache 2.0** | 상용(프로프라이어터리) |
| 실행 | 로컬/직접 스케줄 | 웹 IDE, 스케줄러, CI/CD, 호스팅 문서 |
| 대상 | 직접 운영하는 팀 | 관리형·협업 기능이 필요한 조직 |

---

## 13. 라이선스 & 버전 동향 (2026-06 기준)

- **dbt Core = Apache License 2.0** (2016 최초 릴리스부터 유지). GitHub `dbt-labs/dbt-core`.
- **티어드 라이선스 모델**:
  - dbt Core(SQL 컴파일·DB 연결): **Apache 2.0**
  - dbt Server: **BSL 1.1**(3년 후 Apache 2.0로 전환) — 단, 현재 **deprecated**
  - dbt Cloud의 프록시 서버: **프로프라이어터리**
  - dbt **Fusion** 바이너리 배포본: 일부 **소스 비공개 프로프라이어터리** 컴포넌트 포함(ELv2 + Apache 2.0 + proprietary 혼합)
- **dbt Core v2.0 (2026-06 시점, alpha)**: 기존 **Python 기반 v1**을 **Rust 기반으로 재구현**. dbt **Fusion 엔진**과 동일 기반(ADBC, Apache Arrow, Parquet) 위에 구축되며, **여전히 Apache 2.0**로 공개(이전에 ELv2 예정이던 런타임도 Apache 2.0로 전환).
  - 두 배포본: `dbt-core`(OSS, Apache 2.0) + 프리컴파일 **Fusion 바이너리**(일부 proprietary).
  - **주의**: v2.0은 **alpha**, **v1(Python)이 여전히 안정 기본값**. "Python 기반"이라는 설명은 v1에만 해당. Python 코드베이스는 `1.latest` 브랜치로 보존.

> **시점 민감 정보 경고**: 위 라이선스/버전 사실은 2026-06 기준으로 변동성이 크다. v2.0의 GA 시점, v1↔v2 마이그레이션 호환성은 추후 확인 필요. (이전에 인용되던 `getdbt.com/blog/licensing-dbt`는 404 → `getdbt.com/licenses-faq`, `docs.getdbt.com/blog/dbt-core-v2-is-here` 참조.)

---

## 참고 자료 (1차 출처)

- dbt 공식 문서: https://docs.getdbt.com/docs/introduction
- GitHub: https://github.com/dbt-labs/dbt-core
- Jinja & 매크로: https://docs.getdbt.com/docs/build/jinja-macros
- Materializations: https://docs.getdbt.com/docs/build/materializations
- Data tests: https://docs.getdbt.com/docs/build/data-tests
- Sources / Seeds / Snapshots: https://docs.getdbt.com/docs/build/{sources,seeds,snapshots}
- Best practices(레이어링): https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview
- 지원 플랫폼: https://docs.getdbt.com/docs/supported-data-platforms
- `dbt build` / 노드 선택: https://docs.getdbt.com/reference/commands/build, /reference/node-selection/syntax
- 라이선스: https://www.getdbt.com/licenses-faq, https://docs.getdbt.com/blog/dbt-core-v2-is-here
- "What exactly is dbt?" (Tristan Handy, Fishtown Analytics): https://medium.com/fishtown-analytics/what-exactly-is-dbt-47ba57309068
