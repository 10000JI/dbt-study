# Apache DataFusion — 이론

<!-- > 데이터 엔지니어링 학습 노트. **Rust로 작성된, Apache Arrow 기반의 확장형(extensible) 쿼리 엔진**.
> 모든 핵심 사실은 1차 출처(datafusion.apache.org, Arrow/ASF 블로그, ASF News, GitHub)로 교차 검증함 (기준: 2026-06). -->

<!-- --- -->

## 1. Apache DataFusion이란?

- **공식 정의(태그라인)**: *"DataFusion is an extensible query engine written in Rust that uses Apache Arrow as its in-memory format."* (Rust로 작성된 확장형 쿼리 엔진, **Apache Arrow를 인메모리 포맷으로 사용**)
- **상세 정의**: Rust로 **데이터 중심 시스템을 구축**하기 위한, 매우 빠르고 확장 가능한 쿼리 엔진. Apache Arrow 인메모리 포맷 사용.
- **성격(중요)**: DataFusion은 **완성형 데이터베이스가 아니라**, 개발자가 **자신만의 DB/분석 시스템을 만들기 위한 라이브러리 + 바이너리 모음**이다.
  - 공식 표현: *"libraries and binaries for developers building fast and feature rich database and analytic systems, customized to particular workloads."*
  - 활용 예: 도메인 특화 쿼리 엔진, 새로운 DB 플랫폼·데이터 파이프라인, 새로운 쿼리 언어 등.
- **두 가지 API 기본 제공**: **SQL**과 **DataFrame API**를 둘 다 out-of-the-box로 제공.
- **실행 엔진 특성**: *"Blazingly fast, vectorized, multithreaded, streaming execution engine"* — **벡터화(vectorized) · 멀티스레드 · 스트리밍 · 파티션 기반** 실행.
- **라이선스**: **Apache License 2.0**.

> **DataFusion의 위치**: **단일 노드·인메모리 쿼리 엔진을 "라이브러리"로 임베드**해 직접 쿼리를 실행한다. 자체 실행 엔진을 가지며, 컬럼형(Arrow) 벡터화로 매우 빠르다. 분산 처리가 필요하면 별도 프로젝트 **Ballista**를 사용한다(→ 9장). 같은 단일 노드 임베디드 분석 엔진인 **DuckDB**, 분산 엔진 **Spark**와의 비교는 9장 참조.

---

## 2. 등장 배경 & 역사

### 2.1 창시자와 시작

- **창시자**: **Andy Grove** (GitHub `agrove`). ASF News 공식 발표는 그를 "DataFusion의 원 창시자(original creator)"로 명시.
- **시작 시점**: **2017년경 개인 프로젝트**로 출발 (2019년 기증 블로그가 "started two years ago"로 기술).

### 2.2 Apache Arrow 기증 (2019)

- **2019년 2월 4일**, DataFusion이 **Apache Arrow 프로젝트에 기증(donation)** 되어 Arrow의 **하위 프로젝트**가 됨.
- 당시 기술: "Rust 구현 Apache Arrow를 위한 인메모리 쿼리 엔진"이며 "최근 **Arrow 네이티브**로 재구현됨". 기증 시점 기능은 제한적이었음 — RecordBatch 이터레이터에 대한 SQL, CSV 지원, `SELECT/WHERE`, 단순 집계(MIN·MAX·SUM)·`GROUP BY` 수준. (Parquet은 당시 계획 단계)
- 당시 DataFusion 커뮤니티가 단독 독립할 만큼 크지 않아 **Arrow 프로젝트가 약 5년간 인큐베이팅**.

### 2.3 Apache 최상위 프로젝트(TLP) 승격 (2024)

DataFusion은 5년간 성장(GitHub 5,000+ stars, 수십 개 다운스트림, SIGMOD 2024 논문 채택, Apple이 시작한 Spark 가속기 Comet 등) 후 **2024년 독립 TLP로 승격**. 관련 날짜는 **이벤트별로 구분** 필요:

| 날짜 | 이벤트 |
| --- | --- |
| **2024-04-16** | ASF 이사회 결의안 만장일치 통과 → **공식 TLP가 된 날** |
| **2024-05-07** | Arrow 블로그 "Apache Arrow DataFusion is now Apache DataFusion" (**이름 변경 발표**) |
| **2024-06-11** | ASF News 공식 보도자료 게시 |

- 승격과 함께 이름이 "Apache Arrow DataFusion" → **"Apache DataFusion"** 으로 변경됨.

### 2.4 라이선스 & 릴리스 케이던스

- **라이선스**: **Apache License 2.0**. 주 언어 Rust(저장소의 ~99%).
- **릴리스 케이던스**: 대략 **매월 1회 메이저 릴리스**(브레이킹 API 변경 포함). 패치 릴리스는 애드혹.
  - 최근 흐름(2025~2026): 50.x(2025-09) → 51.x → 52.x → 53.x(2026년 봄) 등 월 1 메이저 패턴 유지. *(개별 릴리스의 정확한 일자는 GitHub Releases에서 확인 권장 — 일부 미검증)*

---

## 3. 설계 철학 & 특징

### 3.1 Apache Arrow 네이티브 (컬럼형 인메모리)

DataFusion을 이해하려면 그 기반 기술인 **Apache Arrow**를 먼저 알아야 한다. DataFusion은 데이터를 Arrow 포맷으로 메모리에 올리고 **RecordBatch 단위로 처리**한다.

#### (1) Apache Arrow란?

- **정의**: **언어 독립적(language-agnostic)인 컬럼형(columnar) 인메모리 데이터 포맷 "표준 사양(specification)"** + 이를 구현한 다언어 라이브러리 모음.
- 공식 표현: *"a language-independent columnar memory format for flat and nested data, organized for efficient analytic operations on modern hardware."*
- 핵심은 단순 라이브러리가 아니라 **"표준 포맷"** 이라는 점이다. 시스템마다 제각각인 인메모리 표현(단편화)을 **공통 데이터 계층**으로 통일하여, 서로 다른 엔진·언어가 같은 데이터를 변환 없이 주고받게 한다.
- **역사**: ASF 최상위 프로젝트로 **2016년 2월 17일 발표**, 최초 릴리스 2016년 10월 10일. 초기 코드/Java 라이브러리는 **Apache Drill**에서 시드됨. *(창시자로 널리 알려진 Wes McKinney(pandas 창시자)·Jacques Nadeau 등은 위키피디아 본문에 이름이 명시돼 있지 않아 부분 미검증.)*

#### (2) 행(row) vs 열(columnar) 메모리 레이아웃

| 레이아웃 | 저장 방식 | 유리한 워크로드 |
| --- | --- | --- |
| **행 기반(row-oriented)** | 한 레코드의 모든 필드를 연속 배치 | OLTP(단건 행 조회/수정) |
| **열 기반(columnar)** | 같은 컬럼의 값들을 연속 배치 | **OLAP(분석/집계)** |

- 컬럼 단위 연속 저장의 이점:
  - **벡터화/SIMD**: 같은 타입 값이 연속되어 *"SIMD(Single Instruction, Multiple Data)"* 연산으로 한 번에 다수 값 처리. 사양은 **64바이트 정렬**을 권장.
  - **캐시 효율**: CPU 캐시/메모리 대역폭을 효율적으로 사용.
  - **압축 친화**: 동일 타입·유사 분포 값이 모여 인코딩/압축에 유리.

#### (3) 핵심 개념 — Schema · Array · RecordBatch

- **Schema**: 이름이 부여된 **Field**들의 순서 있는 집합(컬럼 구조 정의). Field = 이름 + **DataType** (+ nullable).
- **Array**: 같은 타입 값들의 시퀀스, 길이를 앎, **불변(immutable)**. 구성 = DataType + 메모리 버퍼들 + length + null count.
- **RecordBatch**: 스키마를 따르는 **Array(컬럼)들의 묶음이며 모든 컬럼 길이가 동일** → 테이블의 **수평 청크(horizontal slice)**. ← *DataFusion 실행의 기본 단위*.
- **물리 버퍼 구조**:
  - **Validity bitmap**: null 표현 전용 버퍼(비트 1 = non-null, 0 = null).
  - **고정폭 타입**: validity bitmap + values buffer.
  - **가변 길이(string 등)**: **offsets buffer + data buffer** (슬롯 길이 = `offsets[j+1] - offsets[j]`).

#### (4) 제로카피(zero-copy) 상호운용 — Arrow의 가장 큰 가치

- 표준화된 동일 인메모리 표현 덕분에, 서로 다른 시스템/언어가 **직렬화·역직렬화 없이 같은 메모리 버퍼를 공유**한다: *"zero-copy reads for lightning-fast data access without serialization overhead."*
- 분석 워크로드에서 직렬화는 컴퓨팅 비용의 상당 부분을 차지할 수 있는데(FAQ는 80~90%까지 언급), Arrow는 이를 제거한다. → pandas ↔ Spark ↔ DataFusion ↔ Parquet 리더 간 데이터 이동 비용이 거의 0.

#### (5) 생태계 구성요소

- **Arrow Columnar Format**(인메모리 스펙), **Arrow IPC**(파일/스트림 직렬화 포맷), **Arrow Flight**(고성능 네트워크 데이터 전송), **Compute kernels**(벡터화 연산), **ADBC**(Arrow Database Connectivity).
- **언어 구현체**: C++, **Rust(arrow-rs)**, Python(pyarrow), Java, Go, C#, JS 등. → **DataFusion은 이 중 Rust 구현인 `arrow-rs`의 Array/Schema/compute kernel 위에서 동작**한다.

#### (6) Arrow vs Parquet (자주 헷갈리는 포인트)

둘 다 컬럼형이지만 **목적이 다른 상호 보완 관계**다.

| 구분 | Apache **Arrow** | Apache **Parquet** |
| --- | --- | --- |
| 위치 | **인메모리(in-memory)** | **온디스크(on-disk)** |
| 목적 | CPU 처리·연산 최적화 | 저장 공간 효율 최적화 |
| 압축 | 보통 **비압축**(CPU 자연 포맷) | **압축** 저장 |
| 접근 | 임의 위치 즉시 접근 | 메모리로 읽으며 디코딩 필요 |

> 권장 패턴: **Parquet으로 디스크에 저장 → Arrow 포맷으로 메모리에 읽어 연산**. DataFusion이 정확히 이 패턴(Parquet 1급 지원 + Arrow 실행)을 따른다.

#### (7) 한 줄 요약

> DataFusion은 데이터를 **Arrow 컬럼형 포맷(RecordBatch)** 으로 메모리에 올려 **벡터화·병렬**로 처리하고, 표준 포맷이므로 다른 Arrow 기반 시스템과 **제로카피로 상호운용**한다. RecordBatch는 **불변 스냅샷**이라 동기화 없이 안전하게 동시 처리된다.

### 3.2 확장성 (Extensible) — 핵심 가치

- DataFusion의 정체성은 "**커스터마이즈 가능한 빌딩 블록**"이다. 사용자는 다음을 자유롭게 교체·추가할 수 있다:
  - 사용자 정의 함수: **스칼라 UDF / 집계 UDAF / 윈도우 UDWF**
  - 커스텀 데이터소스(`TableProvider`) 및 SQL 확장
  - 커스텀 plan/execution 노드(연산자)
  - **Optimizer pass**(최적화 패스)
  - 언어 바인딩: Python, Java, Ruby, C

### 3.3 고성능 실행

- 벡터화 + 멀티스레드 + **파티션 기반 병렬 실행** + **async 스트리밍 IO**. ClickBench 등 벤치마크에서 단일 노드 Parquet 쿼리 최상위권 성능 보고.

---

## 4. 아키텍처 — 쿼리 실행 흐름

SQL 또는 DataFrame API로 들어온 쿼리는 다음 단계를 거친다:

```
[SQL 문자열]  또는  [DataFrame API]
      │
      ▼
1) SQL 파싱 (sqlparser-rs)          → AST
      ▼
2) LogicalPlan 생성                 → 논리 계획
      ▼
3) 논리 최적화 (Logical Optimization) → 최적화된 LogicalPlan
      ▼
4) 물리 계획 (Physical Planning)     → ExecutionPlan 생성
      ▼
5) 물리 최적화 (Physical Optimization)→ 최적화된 ExecutionPlan
      ▼
6) 실행 (Execution)                 → Apache Arrow RecordBatch 스트림 산출
                                      (벡터화·파티션 병렬·async)
```

### 4.1 논리 최적화 규칙 (대표 예시)

EXPLAIN VERBOSE에서 관찰되는 규칙들(버전마다 이름/개수 변동). 핵심 푸시다운:

- **projection_push_down** (프로젝션 푸시다운, 불필요 컬럼 제거)
- **filter_push_down** (= predicate pushdown, 술어 푸시다운)
- **limit_push_down**
- 그 외: `type_coercion`(타입 강제), `simplify_expressions`(식 단순화), `eliminate_filter/limit`, `common_sub_expression_eliminate`(공통식 제거), 서브쿼리 디코릴레이션(`decorrelate_where_exists/in`, `scalar_subquery_to_join`) 등.

### 4.2 물리 최적화 규칙 (대표 예시)

- `aggregate_statistics`, `join_selection`(조인 알고리즘 선택), `coalesce_batches`(배치 병합), **`repartition`(파티션 기반 병렬화)**, `add_merge_exec`.
- **비용 기반 요소**: 컬럼 통계 + interval arithmetic(인터벌 산술)로 선택도(selectivity) 추정.

> *(주의)* 위 규칙 목록은 문서의 EXPLAIN 예시 기준 "대표 예시"이며, 최신 50번대 버전에는 규칙이 더 많고 일부 이름이 다를 수 있음. (`sqlparser-rs`가 SQL 파서라는 점은 생태계에서 통용되는 사실이나 문서 직접 인용은 부분 미검증.)

---

## 5. 핵심 구성요소 & 확장 포인트

| 구성요소 | 역할 |
| --- | --- |
| **SessionContext** | 진입점. 데이터 등록 · SQL 실행 · DataFrame 생성의 시작점 (`SessionContext::new()`) |
| **sqlparser-rs** | SQL 문자열 → AST 파서 |
| **LogicalPlan** | 논리 계획 표현 |
| **Logical/Physical Planner** | 논리→물리 계획 변환 |
| **Optimizer 규칙** | 논리/물리 최적화 패스 (push-down 등) |
| **ExecutionPlan (trait)** | 물리 실행 노드. RecordBatch 스트림을 산출 |
| **TableProvider (trait)** | **커스텀 데이터소스/파일 포맷** 연결 인터페이스 |
| **UDF / UDAF / UDWF** | 사용자 정의 스칼라/집계/윈도우 함수 |
| **Catalog / Schema / Table** | 카탈로그·스키마·테이블 추상화 |

### 5.1 커스텀 데이터소스 — `TableProvider`

- `TableProvider` trait를 구현하면 **임의의 데이터소스/파일 포맷**을 SQL/DataFrame에 노출할 수 있다.
- 파일 기반이라면 `ListingTable`이 파일 디스커버리·파티션 컬럼 추론·플랜 구성을 처리하므로, `FileFormat`/`FileSource`/`FileOpener`만 구현하면 된다.

### 5.2 기타

- **Substrait** 쿼리 플랜 지원, 표현식 타입 coercion, 자동 조인 재정렬, 비동기 스트리밍 IO.

---

## 6. 지원 파일 포맷 & 데이터소스

| 구분 | 내용 |
| --- | --- |
| **빌트인 파일 포맷** | **Parquet, CSV, JSON(NDJSON), Avro** (4종) |
| **ORC** | **빌트인 미지원(✗)**. 커뮤니티 확장 `datafusion-contrib/datafusion-orc`(orc-rust, 실험적) 또는 `TableProvider` 직접 구현으로 추가 |
| **객체 스토리지** | **AWS S3 · Azure Blob · Google Cloud Storage** 네이티브 지원, 추가는 **`ObjectStore`(object_store) trait** 로 확장 |

> DataFusion은 **Parquet을 1급 시민**으로 다루는 반면 ORC는 빌트인이 아니라는 점에 유의.

---

## 7. API 사용법 & Rust 예제

공통(비동기 진입점):
```rust
use datafusion::prelude::*;
use datafusion::functions_aggregate::expr_fn::min;
// #[tokio::main] async fn main() -> datafusion::error::Result<()> { ... }
```

**예제 1 — SQL API** (CSV 등록 후 SQL 실행)
```rust
let ctx = SessionContext::new();
ctx.register_csv("example", "tests/data/example.csv", CsvReadOptions::new()).await?;

let df = ctx.sql(
    "SELECT a, MIN(b) FROM example WHERE a <= b GROUP BY a LIMIT 100"
).await?;
df.show().await?;
```

**예제 2 — DataFrame API** (동일 질의를 메서드 체이닝으로)
```rust
let ctx = SessionContext::new();
let df = ctx.read_csv("tests/data/example.csv", CsvReadOptions::new()).await?;

let df = df.filter(col("a").lt_eq(col("b")))?
           .aggregate(vec![col("a")], vec![min(col("b"))])?
           .limit(0, Some(100))?;
df.show().await?;
```

- `.collect()` → 결과를 `Vec<RecordBatch>`로 수집(`df.collect().await?`), `.show()` → 콘솔 출력.
- Parquet은 `register_parquet`/`read_parquet`로 동일 패턴(포맷만 교체).

---

## 8. 임베드/기반 프로젝트 (다운스트림 생태계)

DataFusion은 "엔진을 만드는 엔진"으로서 수많은 시스템에 임베드되어 있다:

| 프로젝트 | 설명 |
| --- | --- |
| **InfluxDB 3.0 (IOx)** | 시계열 DB. DataFusion 채택 이유 — ① Rust 작성 ② Arrow 기반 메모리 상호운용 ③ 확장성(SQL·InfluxQL·Flux 지원) |
| **Apache DataFusion Comet** | **Apache Spark 실행을 네이티브 가속**하는 플러그인. **Apple이 최초 기여** |
| **Ballista** | DataFusion 기반 **분산 SQL 쿼리 엔진**(DataFusion 메이저 버전에 정렬) |
| 기타 | GreptimeDB·CnosDB(시계열), delta-rs·iceberg-rust(레이크), LanceDB, SpiceAI, Cube, Arroyo, OpenObserve, VegaFusion, dask-sql 등 |

> InfluxData 블로그가 꼽은 "7개 DataFusion 프로젝트"와 ASF News의 다운스트림 목록에서 위 사례 확인. (Coralogix·ROAPI 등은 본 리서치 1차 출처로는 미검증.)

---

## 9. 다른 엔진과의 비교

### 9.1 vs DuckDB

- **공통**: 둘 다 단일 노드·임베디드 분석 엔진, 컬럼형·벡터화.
- **차이**:
  - **DuckDB** = **C++로 작성된 "완성형 임베디드 DB"**. 설치 즉시 데이터베이스로 사용.
  - **DataFusion** = **Rust 라이브러리/툴킷**. "커스텀 쿼리 엔진·DB 플랫폼을 구축하는 빌딩 블록"이 본질적 포지셔닝.
- *(주의)* "DuckDB와 동일 위치"라는 직접 비교는 공식 1차 출처의 명시 문장이 아니라 일반적 통설 정리(부분 미검증).

### 9.2 vs Apache Spark

- **Spark** = 분산 처리 엔진(JVM). **DataFusion** = 기본적으로 단일 노드 라이브러리.
- 분산 처리는 별도 프로젝트 **Ballista**가 담당.
- **Comet**으로 Spark 실행을 네이티브 가속(대체가 아니라 가속/플러그인).

**Ballista 분산 아키텍처 (공식 도식):**

![Apache DataFusion Ballista 분산 쿼리 실행 아키텍처 — 클라이언트·스케줄러·익스큐터 상호작용](https://datafusion.apache.org/ballista/_images/ballista_architecture.excalidraw.svg)

> 출처: Ballista 공식 문서 — https://datafusion.apache.org/ballista/contributors-guide/architecture.html
> Ballista는 DataFusion 코어를 분산 환경으로 확장한 것으로, **클라이언트 ↔ 스케줄러 ↔ 익스큐터(executor)** 가 협력해 쿼리를 여러 노드에 분산 실행한다. (이는 *분산 변형*의 도식이며, 4장의 단일 노드 코어 파이프라인과는 다른 계층임에 유의.)

---

## 10. 핵심 사실 빠른 요약

| 항목 | 값 |
| --- | --- |
| 언어 | Rust |
| 인메모리 포맷 | Apache Arrow (RecordBatch) |
| 창시자 | Andy Grove |
| 시작 | 2017년경(개인 프로젝트) |
| Arrow 기증 | 2019-02-04 |
| TLP 이사회 결의 | 2024-04-16 |
| 이름 변경 발표 | 2024-05-07 (Arrow 블로그) |
| ASF 공식 보도 | 2024-06-11 |
| 라이선스 | Apache License 2.0 |
| 릴리스 | 약 월 1회 메이저 |
| 빌트인 포맷 | Parquet · CSV · JSON · Avro |
| ORC | 빌트인 미지원(커뮤니티 확장 존재) |
| API | SQL + DataFrame |

---

## 참고 자료 (1차 출처)

- 공식 사이트 / 소개: https://datafusion.apache.org/ , https://datafusion.apache.org/user-guide/introduction.html
- Arrow 기증(2019): https://arrow.apache.org/blog/2019/02/04/datafusion-donation/
- TLP 승격 발표(2024): https://arrow.apache.org/blog/2024/05/07/datafusion-tlp/
- ASF 공식 보도자료: https://news.apache.org/foundation/entry/apache-software-foundation-announces-new-top-level-project-apache-datafusion
- GitHub: https://github.com/apache/datafusion
- 쿼리 옵티마이저: https://datafusion.apache.org/library-user-guide/query-optimizer.html
- 커스텀 TableProvider: https://datafusion.apache.org/library-user-guide/custom-table-providers.html
- 예제: https://datafusion.apache.org/user-guide/example-usage.html
- 다운스트림 사례: https://www.influxdata.com/blog/7-datafusion-projects-influxdb/
