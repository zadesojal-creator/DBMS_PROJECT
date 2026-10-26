"""
Concurrency & Race Condition Suite (test_concurrency.py)
Validates that 20 simultaneous buy orders competing for limited cash balance
execute safely under row locks without overspending or balance corruption.
"""
import uuid
import threading
from decimal import Decimal
import pytest
from services.trading_service import TradingService
from repositories.account_repo import AccountRepository
from services.portfolio_service import PortfolioService

def test_concurrent_orders_no_overspend(app):
    """
    Spawns 20 concurrent threads trying to buy 20 shares of TCS simultaneously.
    Total requested value ~ ₹8,40,000, which exceeds available balance (~₹1,00,000).
    Guarantees:
    - No negative balance occurs
    - Exact reconciliation holds
    - Handled cleanly without DB lock corruption
    """
    user_id = 6 # Vikram Malhotra
    account_init = AccountRepository.get_by_user_id(user_id)
    initial_cash = Decimal(str(account_init['virtual_balance']))
    if initial_cash < Decimal('50000.00'):
        TradingService.process_deposit(user_id, Decimal('100000.00'))
        account_init = AccountRepository.get_by_user_id(user_id)
        initial_cash = Decimal(str(account_init['virtual_balance']))

    num_threads = 20
    results = []
    threads = []

    def worker():
        with app.app_context():
            key = f"CONCURRENCY_TEST_{uuid.uuid4()}"
            # Attempt to buy 5 shares of TCS (~₹21,000)
            res = TradingService.execute_market_order(
                user_id=user_id,
                stock_id=1,
                side="BUY",
                quantity=5,
                idempotency_key=key
            )
            results.append(res)

    for _ in range(num_threads):
        t = threading.Thread(target=worker)
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Analyze results
    executed = [r for r in results if r["status"] == "EXECUTED"]
    rejected = [r for r in results if r["status"] == "REJECTED"]

    assert len(results) == num_threads
    assert len(executed) > 0
    assert len(rejected) > 0

    account_final = AccountRepository.get_by_user_id(user_id)
    final_cash = Decimal(str(account_final['virtual_balance']))

    # Assert cash is strictly >= 0 and never exceeded
    assert final_cash >= Decimal('0.00')
    assert final_cash < initial_cash

    # Exhaustive reconciliation invariant check
    reconciled = PortfolioService.verify_reconciliation_invariants(user_id)
    assert reconciled["cash_reconciled"] is True
    assert reconciled["holdings_reconciled"] is True

def test_concurrent_deposit_race_condition(app):
    """
    Spawns 10 concurrent threads depositing ₹1,000 into the same account simultaneously.
    Guarantees:
    - Row-locking with SELECT ... FOR UPDATE eliminates lost updates
    - Exactly ₹10,000 is credited
    - Authoritative Account_Ledger signed sum perfectly matches virtual_balance
    """
    user_id = 7  # Neha Sharma
    account_init = AccountRepository.get_by_user_id(user_id)
    initial_cash = Decimal(str(account_init['virtual_balance']))

    num_threads = 10
    deposit_per_thread = Decimal('1000.00')
    threads = []
    errors = []

    def deposit_worker():
        with app.app_context():
            try:
                TradingService.process_deposit(
                    user_id=user_id,
                    amount=deposit_per_thread,
                    idempotency_key=f"DEP_RACE_{uuid.uuid4()}"
                )
            except Exception as e:
                errors.append(e)

    for _ in range(num_threads):
        t = threading.Thread(target=deposit_worker)
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Deposit threads raised errors: {errors}"

    account_final = AccountRepository.get_by_user_id(user_id)
    final_cash = Decimal(str(account_final['virtual_balance']))

    expected_cash = initial_cash + (deposit_per_thread * num_threads)
    assert final_cash == expected_cash

    reconciled = PortfolioService.verify_reconciliation_invariants(user_id)
    assert reconciled["cash_reconciled"] is True

def test_deposit_idempotency(app):
    """
    Submitting the same deposit with identical idempotency_key must be idempotent:
    First call processes deposit and appends ledger row;
    Second call returns cached receipt with idempotent_replayed=True and zero extra balance.
    """
    user_id = 7
    account_before = AccountRepository.get_by_user_id(user_id)
    bal_before = Decimal(str(account_before['virtual_balance']))

    idem_key = f"IDEM_DEP_{uuid.uuid4().hex[:10]}"

    with app.app_context():
        res1 = TradingService.process_deposit(user_id, Decimal('2500.00'), idempotency_key=idem_key)
        assert res1["idempotent_replayed"] is False
        assert Decimal(str(res1["new_virtual_balance"])) == bal_before + Decimal('2500.00')

        # Replay duplicate request
        res2 = TradingService.process_deposit(user_id, Decimal('2500.00'), idempotency_key=idem_key)
        assert res2["idempotent_replayed"] is True
        assert Decimal(str(res2["new_virtual_balance"])) == Decimal(str(res1["new_virtual_balance"]))

        account_after = AccountRepository.get_by_user_id(user_id)
        assert Decimal(str(account_after['virtual_balance'])) == bal_before + Decimal('2500.00')

