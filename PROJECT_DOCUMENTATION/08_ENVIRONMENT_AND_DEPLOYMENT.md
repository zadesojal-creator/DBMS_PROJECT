# StockTrade v2 — Environment Variables & Cloud Deployment Guide

This document catalogs all environment variables, cloud deployment configurations, and operational settings for deploying StockTrade v2 to Render and Aiven Cloud MySQL.

---

## 1. Environment Variables Reference Table

> [!CAUTION]
> **Security Rule**: Never commit actual secret values, API keys, or private certificates to source control. Configure these variables via the cloud hosting provider's secure dashboard or local `.env` files (which are git-ignored).

| Variable Name | Required? | Usage | Default Value | Consuming File | Sensitive? | Render Dashboard Location | Purpose / Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FLASK_ENV` | Recommended | Prod / Dev | `development` | `config.py`, `wsgi.py`, `app.py` | No | Environment Tab | Enforces production security (`DEBUG=False`, `SESSION_COOKIE_SECURE=True`). |
| `SECRET_KEY` | **Required** in Prod | Prod | None (Blocked if default) | `config.py`, `app.py` | **Yes** | Environment Tab | Session cryptographic encryption key (min 32 bytes hex). Generated via `secrets.token_hex(32)`. |
| `PORT` | Optional | Prod | `10000` (Render) / `5000` (Local) | `wsgi.py`, `app.py` | No | Environment Tab | TCP port bound by Gunicorn or Flask. Injected automatically by Render. |
| `START_SIMULATOR` | Optional | Prod / Dev | `true` | `wsgi.py`, `app.py` | No | Environment Tab | Controls whether the market simulator background thread launches on app startup. |
| `DB_HOST` | **Required** | Prod / Dev | `localhost` | `config.py`, `models/db.py` | No | Environment Tab | Hostname of MySQL database (e.g. `mysql-....aivencloud.com`). |
| `DB_PORT` | **Required** | Prod / Dev | `3306` | `config.py`, `models/db.py` | No | Environment Tab | Port of MySQL server (Aiven typically uses dynamic ports, e.g. `11232`). |
| `DB_NAME` | **Required** | Prod / Dev | `stocktrade` | `config.py`, `models/db.py` | No | Environment Tab | Target MySQL database name (default `defaultdb` on Aiven). |
| `DB_USER` | **Required** | Prod / Dev | Falls back to `DB_ROOT_USER` | `config.py`, `models/db.py` | No | Environment Tab | Application DML database user (`avnadmin` on Aiven or `stocktrade_app` locally). |
| `DB_PASSWORD` | **Required** | Prod / Dev | Falls back to `DB_ROOT_PASSWORD` | `config.py`, `models/db.py` | **Yes** | Environment Tab | Database password for application user. |
| `DB_AI_USER` | Optional | Prod / Dev | Falls back to `DB_USER` | `config.py`, `models/db.py` | No | Environment Tab | Read-only AI database user (`stocktrade_ai_ro` or same as `DB_USER`). |
| `DB_AI_PASSWORD` | Optional | Prod / Dev | Falls back to `DB_PASSWORD` | `config.py`, `models/db.py` | **Yes** | Environment Tab | Password for read-only AI database user. |
| `DB_SSL` | Recommended | Prod | `false` (Local) / `true` (Cloud) | `config.py`, `models/db.py` | No | Environment Tab | Enables TLS encryption for database wire traffic. |
| `DB_SSL_CA` | Optional | Prod | Project root `aiven-ca.pem` | `config.py`, `models/db.py` | No | Environment Tab | File path to CA certificate bundle (e.g. `/etc/secrets/aiven-ca.pem`). |
| `DB_SSL_CA_CONTENT` | Optional | Prod | Empty | `config.py`, `models/db.py` | **Yes** | Environment Tab | Raw text content of Aiven Project CA certificate (written to runtime tempfile). |
| `GROK_API_KEY` | Optional | Prod / Dev | Empty | `services/llm_router.py` | **Yes** | Environment Tab | xAI Grok API key for natural language SQL generation. |
| `GEMINI_API_KEY` | Optional | Prod / Dev | Empty | `services/llm_router.py` | **Yes** | Environment Tab | Google Gemini API key for natural language SQL generation. |
| `OPENROUTER_API_KEY`| Optional | Prod / Dev | Empty | `services/llm_router.py` | **Yes** | Environment Tab | OpenRouter multi-provider API key. |
| `MISTRAL_API_KEY` | Optional | Prod / Dev | Empty | `services/llm_router.py` | **Yes** | Environment Tab | Mistral AI API key. |
| `LLM_TIMEOUT_SECONDS`| Optional | Prod / Dev | `5` | `services/llm_router.py` | No | Environment Tab | Maximum timeout in seconds per AI provider before failing over. |
| `LLM_COOLDOWN_SECONDS`| Optional | Prod / Dev | `60` | `services/llm_router.py` | No | Environment Tab | Cooldown window before retrying a provider that returned 429 or timeout. |
| `TEST_DB_NAME` | Optional | Testing | `stocktrade_test` | `config.py`, `tests/conftest.py` | No | Local `.env` | Isolated database name used exclusively by automated pytest runs. |

---

## 2. Render Cloud Web Service Configuration

The project includes an Infrastructure-as-Code Blueprint in [`render.yaml`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/render.yaml):

```yaml
services:
  - type: web
    name: stocktrade-v2
    runtime: python
    plan: free
    region: oregon
    buildCommand: "npm --prefix frontend install && npm --prefix frontend run build && pip install -r requirements.txt"
    startCommand: "gunicorn wsgi:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT"
```

### Architectural Rationale for Render Settings:

1. **Build Command**:
   - `npm --prefix frontend install && npm --prefix frontend run build && pip install -r requirements.txt`
   - Render's native Python runtime includes Node.js and npm pre-installed.
   - Vite builds the React SPA into `static/dist/`, which is then packaged directly with the Flask application.
2. **Start Command**:
   - `gunicorn wsgi:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT`
   - **Crucial Single-Process Concurrency**: Using `--workers 1 --threads 8` guarantees that the `MarketSimulator` singleton thread runs in **exactly one process**, eliminating duplicate tick broadcasts or database lock contention, while 8 worker threads handle incoming HTTP requests concurrently with minimal memory (~70 MB).
3. **Application Entry Point**:
   - `wsgi.py` initializes the Flask app factory (`create_app('production')`) and launches the `MarketSimulator` background worker.
4. **Health Check Probe**:
   - Path: `/health`
   - Returns HTTP 200 `{"status": "healthy", "system": "StockTrade Simulated Platform"}`.

---

## 3. Aiven Cloud MySQL 8.0 & TLS Configuration

StockTrade v2 requires native MySQL 8.0 support for:
- Stored procedures (`sp_execute_trade`, `sp_reconcile_financial_integrity`)
- Triggers (16 ledger immutability and role triggers)
- Row-level locking (`SELECT ... FOR UPDATE`)
- Advisory locks (`GET_LOCK`, `RELEASE_LOCK`)

### Aiven TLS Certificate Validation:
- Aiven MySQL utilizes a custom **Project CA**.
- The certificate must be supplied to the application using either:
  1. **Render Secret File**: Upload `aiven-ca.pem` to Render as a Secret File at `/etc/secrets/aiven-ca.pem` and set `DB_SSL_CA=/etc/secrets/aiven-ca.pem`.
  2. **Render Environment Variable**: Paste the entire PEM text of `aiven-ca.pem` into `DB_SSL_CA_CONTENT`. The application dynamically writes it to a secure temporary file upon boot.
  3. **Repository Root Fallback**: If `aiven-ca.pem` exists in the project root, [`models/db.py`](file:///c:/Users/zades/OneDrive/Pictures/Desktop/DBMSPRJ/models/db.py) automatically resolves its absolute path.
- **PyMySQL TLS Handling**: When `ssl_ca` is supplied, PyMySQL's `_create_ssl_ctx` automatically enforces `verify_mode = ssl.CERT_REQUIRED` and hostname verification without requiring conflicting query parameters.
