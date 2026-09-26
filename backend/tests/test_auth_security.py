import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.rate_limit import (
    InMemoryRateLimiter,
    get_client_ip,
    rate_limit_key,
    register_limiter,
    reset_password_limiter,
)
from app.schemas.auth import RegisterRequest, ResetPasswordRequest, LoginRequest


def test_password_strength_validation():
    # Valid strong password
    valid = RegisterRequest(
        name="Security Tester",
        email="test@example.com",
        password="ValidPassword123!",
    )
    assert valid.password == "ValidPassword123!"

    # Missing uppercase
    with pytest.raises(ValueError, match="uppercase"):
        RegisterRequest(
            name="Security Tester",
            email="test@example.com",
            password="validpassword123!",
        )

    # Missing lowercase
    with pytest.raises(ValueError, match="lowercase"):
        RegisterRequest(
            name="Security Tester",
            email="test@example.com",
            password="VALIDPASSWORD123!",
        )

    # Missing digit
    with pytest.raises(ValueError, match="digit"):
        RegisterRequest(
            name="Security Tester",
            email="test@example.com",
            password="ValidPasswordNoDigit!",
        )

    # Missing symbol
    with pytest.raises(ValueError, match="special symbol"):
        RegisterRequest(
            name="Security Tester",
            email="test@example.com",
            password="ValidPassword123",
        )


def test_reset_password_strength_validation():
    valid = ResetPasswordRequest(
        token="some_token_here",
        new_password="NewSecretPass999#",
    )
    assert valid.new_password == "NewSecretPass999#"

    with pytest.raises(ValueError, match="special symbol"):
        ResetPasswordRequest(
            token="some_token_here",
            new_password="WeakNoSymbol123",
        )


def test_input_normalization():
    req = RegisterRequest(
        name="  John Doe  ",
        email="  USER@Example.COM  ",
        password="SecurePassword123!",
    )
    assert req.name == "John Doe"
    assert req.email == "user@example.com"


def test_get_client_ip_with_x_forwarded_for():
    scope = {
        "type": "http",
        "headers": [
            (b"x-forwarded-for", b"203.0.113.195, 70.41.3.18, 150.172.238.178"),
        ],
        "client": ("10.0.0.1", 12345),
    }
    request = Request(scope)
    ip = get_client_ip(request)
    assert ip == "203.0.113.195"


def test_get_client_ip_without_header():
    scope = {
        "type": "http",
        "headers": [],
        "client": ("192.168.1.50", 12345),
    }
    request = Request(scope)
    ip = get_client_ip(request)
    assert ip == "192.168.1.50"


def test_in_memory_rate_limiter():
    limiter = InMemoryRateLimiter(max_attempts=3, window_seconds=60)
    key = "test_user_key"

    # 3 allowed attempts
    limiter.check(key)
    limiter.check(key)
    limiter.check(key)

    # 4th attempt should raise 429
    with pytest.raises(HTTPException) as exc_info:
        limiter.check(key)
    assert exc_info.value.status_code == 429
    assert "Too many attempts" in exc_info.value.detail
