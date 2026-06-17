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
