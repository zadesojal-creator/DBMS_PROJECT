# Verified SQL Examples per Role

## 1. Investor Examples
- **What is my total unrealized profit and loss across all holdings?**:
  ```sql
  SELECT COALESCE(SUM(unrealized_pnl), 0.00) AS total_unrealized_pnl FROM v_investor_portfolio WHERE user_id = @current_user_id;
  ```

- **Which holding is performing best by return percentage?**:
  ```sql
  SELECT symbol, company_name, quantity, current_price, avg_cost, return_pct FROM v_investor_portfolio WHERE user_id = @current_user_id AND return_pct IS NOT NULL ORDER BY return_pct DESC LIMIT 1;
  ```

- **How much brokerage have I paid in total?**:
  ```sql
  SELECT COALESCE(SUM(brokerage_fee), 0.00) AS total_brokerage_paid FROM v_investor_transactions WHERE user_id = @current_user_id;
  ```

- **Show my portfolio allocation by sector**:
  ```sql
  SELECT sector, SUM(market_value) AS sector_value FROM v_investor_portfolio WHERE user_id = @current_user_id GROUP BY sector ORDER BY sector_value DESC;
  ```

---

## 2. Broker Examples
- **Which clients have traded over ₹50,000 in volume?**:
  ```sql
  SELECT investor_name, investor_email, total_volume, total_trades FROM v_broker_client_summary WHERE broker_id = @current_user_id AND total_volume >= 50000.00 ORDER BY total_volume DESC;
  ```

- **What is my total commission earned this month?**:
  ```sql
  SELECT COALESCE(SUM(commission_amount), 0.00) AS total_monthly_commission FROM v_broker_commissions WHERE broker_id = @current_user_id AND YEAR(created_at) = YEAR(CURRENT_DATE) AND MONTH(created_at) = MONTH(CURRENT_DATE);
  ```

- **Who are my top 5 clients by commission generated?**:
  ```sql
  SELECT investor_name, SUM(commission_amount) AS total_commission FROM v_broker_commissions WHERE broker_id = @current_user_id GROUP BY investor_id, investor_name ORDER BY total_commission DESC LIMIT 5;
  ```

---

## 3. Admin Examples
- **What are the top 5 most traded stocks by volume today?**:
  ```sql
  SELECT symbol, SUM(quantity) AS total_shares_traded, SUM(gross_amount) AS total_turnover FROM v_admin_trade_facts WHERE DATE(executed_at) = CURRENT_DATE GROUP BY stock_id, symbol ORDER BY total_turnover DESC LIMIT 5;
  ```

- **What is the total platform brokerage collected across all users?**:
  ```sql
  SELECT COALESCE(SUM(brokerage_fee), 0.00) AS total_platform_brokerage FROM v_admin_trade_facts;
  ```

- **Which accounts have failed login attempts recorded or are locked?**:
  ```sql
  SELECT username, email, role, status, failed_login_attempts, locked_until, last_login_at FROM v_admin_user_audit WHERE failed_login_attempts > 0 OR locked_until IS NOT NULL ORDER BY failed_login_attempts DESC;
  ```

- **Show recent failed login attempts and security events**:
  ```sql
  SELECT username, role, action, ip_address, created_at FROM v_admin_audit_logs WHERE action IN ('LOGIN_FAILED', 'SECURITY_LOCKOUT') ORDER BY created_at DESC LIMIT 50;
  ```

- **Show registered user accounts grouped by role**:
  ```sql
  SELECT role, COUNT(*) AS user_count, SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_count FROM v_admin_user_audit GROUP BY role;
  ```
