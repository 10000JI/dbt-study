-- (1) external table 등록 (CLI 방식 — Python의 register_csv에 대응)
CREATE EXTERNAL TABLE customers STORED AS CSV LOCATION 'data/customers.csv' OPTIONS ('has_header' 'true');
CREATE EXTERNAL TABLE orders    STORED AS CSV LOCATION 'data/orders.csv'    OPTIONS ('has_header' 'true');

-- (2) SELECT
SELECT * FROM orders LIMIT 3;

-- (3) 집계
SELECT status, count(*) AS n, sum(amount) AS total FROM orders GROUP BY status ORDER BY status;

-- (4) 조인 (국가별 매출)
SELECT c.country, sum(o.amount) AS revenue
FROM orders o JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.country ORDER BY revenue DESC;

-- (5) 실행계획 (이론 §4)
EXPLAIN SELECT c.country, sum(o.amount) FROM orders o JOIN customers c USING(customer_id) GROUP BY c.country;
