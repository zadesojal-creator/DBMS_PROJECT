# StockTrade — DBMS Concepts & College Viva Guide

This document provides conceptual explanations and viva questions/answers mapping classroom DBMS theory to the concrete implementation in the StockTrade codebase.

---

## 1. ACID Properties in StockTrade

| ACID Property | Theoretical Definition | Concrete Implementation in StockTrade |
|---|---|---|
| **Atomicity** | All operations in a transaction succeed, or all fail completely. | Handled inside `sp_execute_trade`: either the `Orders` row is set to `EXECUTED`, `Holdings` are updated, `Accounts` balance is debited, and `Account_Ledger` entries are written together, or the entire transaction is rolled back with `ROLLBACK`. |
| **Consistency** | State transitions preserve all database invariants and constraints. | Enforced by foreign keys (`ON DELETE RESTRICT`), table checks (`virtual_balance >= 0`, `quantity > 0`), triggers blocking ledger edits, and the reconciliation invariant: `virtual_balance == SUM(ledger)`. |
| **Isolation** | Concurrent transactions do not interfere or observe dirty/intermediate states. | MySQL InnoDB `READ COMMITTED` transaction isolation with explicit pessimistic row locks (`SELECT ... FOR UPDATE` and `SELECT ... FOR SHARE`) in a fixed row-lock sequence. |
| **Durability** | Committed data survives crashes and power outages. | MySQL InnoDB write-ahead redo log (`ib_logfile0`) and transactional doublewrite buffer. |

---

## 2. Stored Procedures vs. Triggers

### Stored Procedure: `sp_execute_trade`
- **Why use a Stored Procedure?**
  Executing a stock order requires reading current price, checking balance, debiting cash, updating holdings, inserting an order row, inserting a transaction row, and appending two ledger rows (BUY/SELL + FEE). Doing this across multiple network round-trips from Python invites latency and race conditions. `sp_execute_trade` executes all 7 operations inside MySQL in a single network round-trip.
- **Fixed Row-Lock Order to Prevent Deadlocks**:
  1. `Accounts` (pessimistic exclusive lock: `FOR UPDATE`)
  2. `Holdings` (pessimistic exclusive lock: `FOR UPDATE`)
  3. `Current_Prices` (shared lock: `FOR SHARE`)

### Triggers: Ledger Immutability & Validation
- **Triggers**:
  - `trg_ledger_block_update`: Raises SQLSTATE `45000` on any `UPDATE` against `Account_Ledger`.
  - `trg_ledger_block_delete`: Raises SQLSTATE `45000` on any `DELETE` against `Account_Ledger`.
  - `trg_broker_client_role_check`: Asserts that `broker_id` has role `BROKER` and `investor_id` has role `INVESTOR` before inserting into `Broker_Clients`.
- **Why Triggers over Application Code?**
  Triggers execute at the database storage engine layer. Even if a developer connects via MySQL Workbench, Python, or an admin script, the database engine itself rejects mutations.

---

## 3. Database Normalization (1NF &rarr; 3NF) & Deliberate Denormalization

### 1NF (First Normal Form)
- All columns contain atomic values (no delimited strings, arrays, or repeating groups).
- Primary keys defined on every table.

### 2NF (Second Normal Form)
- In 1NF and no non-prime attribute depends on a partial candidate key.
- Composite-keyed tables (`Broker_Clients`: `broker_id, investor_id`) have attributes that depend on the complete key.

### 3NF (Third Normal Form)
- In 2NF and no transitive functional dependencies ($X \rightarrow Y \rightarrow Z$).
- Investor balances are NOT stored on the user row; they reside in `Accounts`, separated from identity.
- Historical stock prices reside in `Stock_Prices` partitioned by `(stock_id, recorded_at)`.

### Deliberate Denormalization: `Current_Prices` Table
- **Justification**: In high-frequency trading platforms, reading the latest price of an equity from `Stock_Prices` requires scanning the time-series index: `SELECT price FROM Stock_Prices WHERE stock_id = ? ORDER BY recorded_at DESC LIMIT 1`.
- To avoid scanning millions of historical rows during trade execution, `Current_Prices` maintains a 1-row-per-stock cache of the latest quote. It is updated in $O(1)$ by the simulator and read by `sp_execute_trade`.

---

## 4. Indexing Strategy

1. **Composite Time-Series Index**:
   ```sql
   CREATE INDEX idx_stock_prices_stock_time ON Stock_Prices (stock_id, recorded_at);
   ```
   Enables index-only scans for OHLC candle aggregation (`FIRST_VALUE`, `MAX`, `MIN` partitioned by time bucket).
2. **Idempotency Key Unique Index**:
   ```sql
   CREATE UNIQUE INDEX idx_orders_user_idempotency ON Orders (user_id, idempotency_key);
   ```
   Instantly blocks double-clicks or duplicate submissions at the database engine level.
3. **Ledger Account Timeline Index**:
   ```sql
   CREATE INDEX idx_ledger_account_time ON Account_Ledger (account_id, created_at);
   ```
   Enables sub-millisecond calculation of account balance sums.
4. **Virtual Generated Column Unique Index for Tenant-Broker Multi-Tenancy**:
   ```sql
   active_investor_key BIGINT GENERATED ALWAYS AS (IF(status = 'ACTIVE', investor_id, NULL)) VIRTUAL,
   UNIQUE KEY uq_broker_clients_active (active_investor_key)
   ```
   Allows an investor to have multiple historical `ENDED` broker relationships over time while strictly enforcing at most one `ACTIVE` assigned broker at any moment.

---

## 5. Order Lifecycle Auditing (`Order_Events`)

Instead of overwriting the status of an order silently, the platform implements an append-only audit trail in `Order_Events`:
- `trg_orders_audit_insert`: Automatically logs the initial creation of every order (`from_status: NULL/NEW -> to_status: PENDING`).
- `trg_orders_audit_update`: Captures every status transition (`PENDING -> EXECUTED`, `PENDING -> REJECTED`), recording `order_id`, `from_status`, `to_status`, `reason`, and `event_timestamp`.
- Terminal states (`EXECUTED`, `REJECTED`, `FAILED`) are enforced as immutable by `trg_orders_block_terminal_update`.

---

## 6. Financial Immutability Triggers

To satisfy regulatory and accounting standards, financial tables are protected at the database storage engine level with SQLSTATE `45000` rejection triggers:
- `Account_Ledger`: `trg_ledger_block_update`, `trg_ledger_block_delete`
- `Transactions`: `trg_transactions_block_update`, `trg_transactions_block_delete`
- `Commissions`: `trg_commissions_block_update`, `trg_commissions_block_delete`
- `Audit_Logs`: `trg_audit_logs_block_update`, `trg_audit_logs_block_delete`

Even if a rogue database administrator attempts a direct manual SQL `UPDATE` or `DELETE`, MySQL immediately rejects the query with custom error text: `"strictly append-only: updates/deletions are prohibited"`.

---

## 7. System-Wide Financial Reconciliation (7 Invariants)

Both a dedicated stored procedure (`sp_reconcile_financial_integrity`) and Python service (`ReconciliationService`) verify zero-discrepancy financial invariants:
1. **Cash vs. Ledger Parity**: `Accounts.virtual_balance == SUM(Account_Ledger.amount)`
2. **Holdings vs. Executed Volume**: `Holdings.quantity == SUM(BUY quantity) - SUM(SELL quantity)`
3. **Executed Orders vs. Transactions**: Every `EXECUTED` order has an authoritative `Transactions` record.
4. **Transactions vs. Ledger Entries**: Every transaction has matching principal (`BUY`/`SELL`) and `FEE` ledger entries.
5. **Broker Commission Accuracy**: Broker commission records match active `Commission_Rules` rates and active broker assignments.
6. **No Duplicate Financial Events**: Unique constraints prevent duplicate transactions, commissions, or idempotency keys.
7. **Opening Balance Grants**: Every investor has exactly one initial grant of ₹1,00,000.00.

---

## 8. Backup, Disaster Recovery & Schema Migrations

- **Logical Backup (`database/backup_manager.py` & `backup_db.ps1`)**:
  Executes non-blocking online logical dumps using `mysqldump` with `--routines`, `--triggers`, `--events`, `--single-transaction`, `--quick`, and `--set-gtid-purged=OFF`.
- **Restoration Parity Verification**:
  Automatically restores dumps into an isolated target test database (`stocktrade_test`) and compares table counts, view counts, stored procedure definitions, trigger definitions, and exact row counts per table.
- **Rolling Retention Policy**:
  Maintains the latest $N$ snapshots (default 5) and automatically purges obsolete backups.

---

## 9. MySQL Advisory Locks (`GET_LOCK`)

- **What is it?** Application-level locks managed directly by the MySQL server process: `SELECT GET_LOCK('stocktrade_simulator_lock', 0)`.
- **Why is it needed?** When running multiple Flask processes (or worker threads), multiple instances of the market simulator could attempt to update prices simultaneously, causing price oscillations. The advisory lock guarantees that only the thread holding the named lock executes the price evolution tick.

---

## 10. Sample Viva Questions & High-Scoring Answers

**Q1: How do you guarantee that a user cannot spend more virtual money than they have during concurrent orders?**
> *Answer:* We use a stored procedure (`sp_execute_trade`) running under transaction isolation with an explicit pessimistic lock `SELECT virtual_balance FROM Accounts WHERE user_id = ? FOR UPDATE`. This row lock prevents any other concurrent thread from reading or updating the user's balance until the transaction commits. If the balance minus trade value is negative, the procedure sets status to `REJECTED` and rolls back.

**Q2: What is the purpose of an append-only ledger? Why not just update the account balance?**
> *Answer:* In financial engineering, updating a single balance number destroys the historical audit trail. An append-only ledger (`Account_Ledger`) logs every financial event (`OPENING_GRANT`, `DEPOSIT`, `BUY`, `SELL`, `FEE`) with signed amounts and timestamps. Database triggers block `UPDATE` and `DELETE` queries. We also continuously test the reconciliation invariant: `Accounts.virtual_balance == SUM(Account_Ledger.amount)`.

**Q3: How do you protect the AI Assistant from SQL injection or malicious statements?**
> *Answer:* We use a 5-layer defense pipeline. First, the LLM is only given views (`v_investor_portfolio`), never base tables. Second, the generated SQL is parsed by `sqlglot` AST validator to ensure it is purely a single `SELECT` statement and references only allowed views. Third, it is executed via a read-only MySQL user (`stocktrade_ai_ro`). Fourth, it sets `@current_user_id` to enforce tenant scoping.

**Q4: How did you solve the problem of allowing multiple ended broker assignments while restricting active ones?**
> *Answer:* A traditional unique constraint on `(broker_id, investor_id)` prevents reassigning an investor after a relationship ends. We solved this using a MySQL virtual generated column: `active_investor_key BIGINT GENERATED ALWAYS AS (IF(status = 'ACTIVE', investor_id, NULL)) VIRTUAL` with a `UNIQUE KEY (active_investor_key)`. Since standard SQL unique indexes allow multiple `NULL` values, an investor can have infinite `ENDED` relationships (`NULL`), but at most one `ACTIVE` relationship (`investor_id`), enforced entirely by the storage engine.

**Q5: How does your OHLC market history query avoid `GROUP_CONCAT` truncation?**
> *Answer:* Fragile string-based aggregations using `GROUP_CONCAT` truncate at 1024 bytes when trading volume is high. We replaced it with MySQL 8.0 deterministic analytic window functions (`FIRST_VALUE(price) OVER (PARTITION BY bucket ORDER BY recorded_at ASC, id ASC) AS open_price` and `MAX(price)`, `MIN(price)`). This executes directly on numerical data types using the composite index `(stock_id, recorded_at)`.

