# 1차 시작 가이드 — Track A (매출 학습)

> 환경: macOS · Python 3.9.6 · git 2.50.1 (확인됨)
> 원칙: **직접 쳐보고 → 결과를 관찰하고 → 실습로그에 ✅/메모**. 가이드는 길잡이일 뿐, 손은 직접.
> 데이터셋 상세: `../데이터셋 Track A — 1차 학습.md`

---

> ✅ **현재 상태(이미 완료됨)**: venv 생성 · `dbt-duckdb`(dbt-core 1.10.22 + duckdb 1.10.0) 설치 · jaffle `dbt build` 통과(PASS=28) 확인. 아래 STEP 0·1은 재현/이해용이며, 바로 **STEP 2(관찰)** 부터 직접 해도 됨.
>
> ⚠️ **Python 3.9.6 캡 주의**: 3.9라 dbt가 **1.10.x로 고정**됨. jaffle 레포는 dbt≥1.11을 요구해서 `dbt build` 시 **`--no-version-check`** 필요(아래 반영). 최신 dbt(1.11)와 매끄러운 진행을 원하면 pyenv/brew로 **Python 3.11+** 설치 후 venv 재생성 권장.

## STEP 0 · 환경 준비 (착수, ~30분)

작업 폴더는 여기(`dbt-poc/`). 먼저 가상환경 + dbt-duckdb 설치.

```bash
cd "/Users/n-mjkim/workspace2/test_20260603/dbt-poc"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install dbt-duckdb        # dbt-core + duckdb 어댑터 + duckdb 라이브러리 한 번에
dbt --version                 # 설치 확인 (Core 버전 + duckdb 플러그인 표시되면 OK)
```

> ⚠️ 만약 Python 버전 경고로 설치 실패 시 → pyenv로 3.11 설치 후 그 파이썬으로 venv 재생성.
> `duckdb` CLI는 선택(없어도 됨). dbt-duckdb가 duckdb 파이썬 라이브러리를 포함.

**확인 포인트**: `dbt --version`에 `installed: ...` 와 `duckdb: ...` 가 보이면 성공.

---

## STEP 1 · jaffle_shop_duckdb — dbt 전체 흐름 1분 체감

```bash
# dbt-poc/ 안, venv 활성화 상태에서
git clone https://github.com/dbt-labs/jaffle_shop_duckdb.git
cd jaffle_shop_duckdb
pip install -r requirements.txt    # 이미 dbt-duckdb 있으면 빠르게 통과
dbt build --no-version-check       # seeds 적재 → 모델 빌드 → 테스트 (3.9→dbt1.10이라 플래그 필요)
```
> 프로파일 못 찾는 에러가 나면 레포 폴더에서 `DBT_PROFILES_DIR="$PWD" dbt build --no-version-check`.

**확인 포인트 (관찰하고 로그에 적기)**
- `dbt build` 출력에서 **seed → model → test** 순서로 도는지
- 통과/실패 카운트(PASS/ERROR) — 몇 개 모델·몇 개 테스트인지
- 끝에 생성된 `jaffle_shop.duckdb` 파일이 폴더에 생겼는지

```bash
dbt docs generate
dbt docs serve     # 브라우저 열림 → Lineage(우하단 초록 버튼)로 DAG 확인
# 확인 끝나면 Ctrl+C
```
**확인 포인트**: customers / orders 모델이 stg_* 들과 어떻게 연결되는지 **lineage 그래프**로 눈으로.

---

## STEP 2 · 내부 들여다보기 — ref() 치환 확인 (핵심)

```bash
# 컴파일된 SQL 열어보기 (ref()가 실제 테이블명으로 바뀐 것 확인)
cat target/compiled/jaffle_shop/models/customers.sql
```
**확인 포인트**: 모델 소스의 `{{ ref('stg_customers') }}` 가 컴파일본에서 **실제 `"jaffle_shop"."main"."stg_customers"`** 같은 식별자로 치환된 걸 직접 비교.

```bash
# DuckDB에 실제로 뭐가 생겼는지 직접 조회 (파이썬으로)
python -c "import duckdb; con=duckdb.connect('jaffle_shop.duckdb'); print(con.sql('show tables')); print(con.sql('select * from customers limit 5'))"
```

---

## STEP 3 · 살짝 만져보기 (선택, 개념 정착)

- `models/` 안의 `stg_customers.sql` 한 줄 바꿔보고 `dbt run -s stg_customers` → 결과 변화 관찰
- `dbt test -s orders` 처럼 특정 모델만 테스트
- 일부러 테스트를 깨서(`schema.yml`에서 not_null 컬럼에 null 만들기) **실패 메시지** 보기

---

## ✅ STEP 1차-1 완료 기준
- [ ] venv + dbt-duckdb 설치, `dbt --version` 확인
- [ ] jaffle `dbt build` 통과, `jaffle_shop.duckdb` 생성
- [ ] `dbt docs serve`로 lineage 확인
- [ ] 컴파일된 SQL에서 `ref()` 치환 눈으로 확인
- [ ] 관찰 내용을 `실습로그.md`에 기록

→ 끝나면 다음: **Olist 9개 테이블 staging 스캐폴딩**(별도 가이드로 진행)

---

## 막히면
- `dbt debug` 로 연결/프로젝트 진단
- 에러 메시지를 실습로그에 붙여두면 같이 해결 가능
