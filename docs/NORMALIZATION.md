# Database Normalization & Schema Design (NORMALIZATION.md)

This document walks through the normalization steps (1NF → 2NF → 3NF / BCNF) applied to the **StockTrade** relational schema, along with intentional denormalizations justified by performance, atomicity, and financial integrity.

---

## 1. First Normal Form (1NF)
A relation is in 1NF if and only if all domain values are atomic and there are no repeating groups.
- **Atomic Attributes**:
  - Full address / contact information split into discrete atomic fields (`phone`, `email`).
  - Monetary values stored as atomic fixed-point numeric scalars (`DECIMAL(15,2)` for money, `DECIMAL(12,4)` for prices).
  - No comma-separated strings for holdings or orders; individual transactions and orders are stored as independent tuples.
- **Unique Primary Keys**:
  - Every entity possesses an immutable surrogate primary key (`BIGINT AUTO_INCREMENT` or compound natural key where appropriate).

---

## 2. Second Normal Form (2NF)
A relation is in 2NF if it is in 1NF and every non-prime attribute is fully functionally dependent on the entire primary key (no partial dependencies).
- In composite relationship tables (e.g., `Holdings` where key is `(user_id, stock_id)` or `Watchlist`):
  - In `Holdings`, `quantity` and `avg_cost` depend strictly on both the `user_id` AND the `stock_id`.
  - Stock descriptive metadata (`company_name`, `sector`, `exchange`) is not repeated inside `Holdings` or `Orders`; it resides exclusively in `Stocks`.
  - User details (`full_name`, `email`, `role`) are not repeated in `Transactions` or `Commissions`; they reference `Users(id)`.

---

## 3. Third Normal Form (3NF)
A relation is in 3NF if it is in 2NF and there are no transitive dependencies (no non-prime attribute depends on another non-prime attribute: $X \to Y$ and $Y \to Z$).
- **Elimination of Transitive Dependencies**:
  - In `Broker_Clients`: tracks assignment between `broker_id` and `investor_id`. Investor's account balance or email is not stored here; it is queried via foreign key join.
  - In `Transactions`: references `order_id`, `user_id`, `stock_id`. The calculated brokerage fee and execution price are frozen at trade execution time to preserve historical contract accuracy.
  - In `Commissions`: references `transaction_id`. The `rate_applied` and `base_brokerage` are recorded directly to preserve immutability even if `Commission_Rules` changes in the future.

---

## 4. Deliberate Denormalizations and Technical Justifications

### 4.1. `Current_Prices` (1:1 Cache with `Stocks`)
- **Normalized Alternative**: Retrieve the latest price via subquery:
  ```sql
  SELECT price FROM Stock_Prices 
  WHERE stock_id = :id ORDER BY recorded_at DESC LIMIT 1;
  ```
- **Reason for Denormalization**:
  1. **High Concurrency Order Execution**: The trading stored procedure `sp_execute_trade` must acquire an exclusive row lock on the current price (`SELECT price FROM Current_Prices WHERE stock_id = :id FOR UPDATE`). Locking a 100,000+ row append-only table `Stock_Prices` would cause severe index lock contention and gap locking.
  2. **High-Frequency Polling**: Hundreds of connected clients poll `/api/v1/market/prices` every 3 seconds. Reading from a compact 100-row table cached in memory avoids scanning time-series partitions.
  3. **Daily OHLC Tracking**: Caching `day_open`, `day_high`, `day_low`, `previous_close`, and `volume` provides instant percentage change metrics without aggregating thousands of 1-minute ticks on every HTTP request.

### 4.2. `Account_Ledger.balance_after`
- **Normalized Alternative**: Recompute balance on every ledger insert as $\sum(\text{amount})$.
- **Reason for Denormalization**:
  1. **Audit Trail & Point-in-Time Verification**: Storing `balance_after` provides an immediate verification check for every journal entry, enabling $O(1)$ reconciliation invariant testing:
     $$\text{Accounts.virtual\_balance} == \text{latest Account\_Ledger.balance\_after} == \sum(\text{Account\_Ledger.amount})$$
  2. **Reconciliation Invariant**: Tested in unit tests after every single trade and deposit.

### 4.3. `Holdings.avg_cost` and `Holdings.quantity`
- **Normalized Alternative**: Compute current holdings and average cost dynamically from the entire transaction history via window functions.
- **Reason for Denormalization**:
  1. $O(1)$ fast check during sell order validation: instant validation if `holding.quantity >= sell_quantity` without aggregating all prior transactions.
  2. Weighted average cost recalculation on BUY is strictly maintained transactionally:
     $$\text{new\_avg} = \frac{(\text{old\_qty} \times \text{old\_avg}) + (\text{qty} \times \text{price})}{\text{old\_qty} + \text{qty}}$$

---

## Summary of Functional Dependency Mapping

| Table | Determinant (Candidate Key) | Dependent Attributes | Normal Form |
| :--- | :--- | :--- | :--- |
| `Users` | `id` (or `email`, `username`) | `password_hash`, `full_name`, `role`, `status`, etc. | 3NF / BCNF |
| `Accounts` | `id` (or `user_id`) | `virtual_balance`, `currency`, `status` | 3NF / BCNF |
| `Stocks` | `id` (or `symbol`) | `company_name`, `sector`, `exchange`, `status` | 3NF / BCNF |
| `Current_Prices` | `stock_id` | `price`, `previous_close`, `day_open`, `day_high`, `day_low`, `volume` | 3NF (Controlled Denorm) |
| `Stock_Prices` | `id` (or `stock_id, recorded_at`) | `price`, `volume`, `source` | 3NF |
| `Orders` | `id` (or `user_id, idempotency_key`) | `stock_id`, `side`, `quantity`, `status`, `idempotency_key` | 3NF |
| `Holdings` | `id` (or `user_id, stock_id`) | `quantity`, `avg_cost`, `updated_at` | 3NF (Controlled Denorm) |
| `Transactions` | `id` (or `order_id`) | `user_id`, `stock_id`, `side`, `quantity`, `execution_price`, `gross_amount`, `brokerage_fee`, `net_amount`, `realized_pnl` | 3NF |
| `Account_Ledger` | `id` | `account_id`, `entry_type`, `amount`, `balance_after`, `reference_type`, `reference_id` | 3NF (Append-Only) |
| `Broker_Clients` | `id` | `broker_id`, `investor_id`, `status`, `assigned_at`, `ended_at` | 3NF |
| `Commissions` | `id` (or `transaction_id`) | `broker_id`, `investor_id`, `base_brokerage`, `rate_applied`, `commission_amount` | 3NF |
