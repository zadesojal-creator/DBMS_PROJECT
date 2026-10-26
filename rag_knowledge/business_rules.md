# StockTrade Financial Business Rules for SQL Queries

1. **Brokerage Charges (Investor-Paid)**:
   - Rate: 0.10% (`0.0010`) of gross trade value (`quantity * price`).
   - Minimum: ₹1.00.
   - Deducted from investor's cash on both BUY and SELL.

2. **Broker Commission (Platform-Funded)**:
   - Rate: 40% (`0.40`) of the investor brokerage collected.
   - Platform-funded and reporting-only: Does NOT cost investor extra, and is NOT deducted from investor.
   - Generated only for investors with an active broker assignment.

3. **Weighted Average Cost Basis & Profit/Loss (P&L)**:
   - On BUY: `new_avg = (old_qty * old_avg + qty * price) / (old_qty + qty)`.
   - On SELL: Average cost does not change on partial sale.
   - Realized P&L (Realized Profit and Loss) on SELL: `(sell_price - avg_cost) * qty - sell_brokerage`.
   - Unrealized P&L (Unrealized Profit and Loss): `(current_price - avg_cost) * quantity`.

4. **Security & Scoping**:
   - Investor queries are scoped to their own `user_id = @current_user_id`.
   - Broker queries are scoped to `broker_id = @current_user_id`.
   - Queries must use SELECT only. Write/mutation queries are strictly blocked.
