"""
Tests for Broker Client Management & Tenant Isolation (tests/test_broker_clients.py)
"""
import uuid
import pytest
from repositories.user_repo import UserRepository
from repositories.broker_repo import BrokerRepository
from repositories.account_repo import AccountRepository

def test_broker_client_onboard_atomicity(broker_client):
    """Verify broker onboarding creates user, account with virtual grant, and active broker assignment."""
    unique_suffix = uuid.uuid4().hex[:8]
    unique_name = f"client_{unique_suffix}"
    payload = {
        "username": unique_name,
        "email": f"{unique_name}@stocktrade.local",
        "full_name": "Test Onboarded Client",
        "password": "Password123!",
        "phone": "9876543210"
    }
    res = broker_client.post("/broker/api/v1/broker/clients", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["ok"] is True
    investor_id = data["data"]["investor_id"]

    # Verify user was created
    user = UserRepository.get_by_id(investor_id)
    assert user is not None
    assert user["role"] == "INVESTOR"

    # Verify virtual balance
    account = AccountRepository.get_by_user_id(investor_id)
    assert account is not None
    assert float(account["virtual_balance"]) == 100000.00

    # Verify broker assignment (Broker Arun is id=2)
    assert BrokerRepository.is_assigned(2, investor_id) is True

def test_broker_tenant_isolation_404_enforced(broker2_client):
    """
    Verify tenant isolation: Broker Priya (id=3) attempting to view Broker Arun's client (Rahul, id=4)
    must receive 404 NOT FOUND (never 403, preventing resource enumeration).
    """
    res = broker2_client.get("/broker/api/v1/broker/client-profile?investor_id=4")
    assert res.status_code == 404
    data = res.get_json()
    assert data["ok"] is False
    assert data["error"]["code"] == "NOT_FOUND"

def test_broker_end_assignment(broker_client):
    """Verify broker can cleanly end relationship with an assigned investor."""
    # Create client under Broker Arun (id=2) with unique username
    unique_name = f"end_{uuid.uuid4().hex[:8]}"
    uid = BrokerRepository.onboard_client(
        broker_id=2,
        username=unique_name,
        email=f"{unique_name}@stocktrade.local",
        full_name="Client To End",
        password_hash="testhash"
    )
    assert BrokerRepository.is_assigned(2, uid) is True

    # End relationship via broker_client
    res = broker_client.post(f"/broker/api/v1/broker/clients/{uid}/end")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True

    # Verify relationship ended
    assert BrokerRepository.is_assigned(2, uid) is False

def test_broker_multiple_ended_assignments_and_single_active_constraint(app):
    """
    Validates virtual generated column active_investor_key:
    - An investor can accumulate multiple ENDED historical assignments.
    - An investor can NEVER have two concurrent ACTIVE assignments.
    """
    from models.db import get_engine
    from sqlalchemy import text
    import pymysql

    unique_name = f"reassign_{uuid.uuid4().hex[:8]}"
    with app.app_context():
        uid = BrokerRepository.onboard_client(
            broker_id=2,
            username=unique_name,
            email=f"{unique_name}@stocktrade.local",
            full_name="Multi Assign Client",
            password_hash="testhash"
        )

        # 1. End assignment with Broker 2
        BrokerRepository.end_assignment(2, uid)
        assert BrokerRepository.is_assigned(2, uid) is False

        # 2. Assign to Broker 3 as ACTIVE
        BrokerRepository.assign_client(3, uid)
        assert BrokerRepository.is_assigned(3, uid) is True

        # 3. End assignment with Broker 3
        BrokerRepository.end_assignment(3, uid)
        assert BrokerRepository.is_assigned(3, uid) is False

        # 4. Check historical records count (should be at least 2 ENDED records)
        with get_engine().connect() as conn:
            cnt = conn.execute(
                text("SELECT COUNT(*) FROM Broker_Clients WHERE investor_id = :uid AND status = 'ENDED'"),
                {"uid": uid}
            ).scalar()
            assert cnt >= 2

        # 5. Activate with Broker 2
        BrokerRepository.assign_client(2, uid)
        assert BrokerRepository.is_assigned(2, uid) is True

        # 6. Attempt concurrent ACTIVE assignment with Broker 3: MUST raise duplicate key error
        with pytest.raises(Exception) as exc_info:
            BrokerRepository.assign_client(3, uid)
        assert "active_investor" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

