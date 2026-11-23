# Inventory & Order Management Platform

Full-stack Inventory & Order Management Platform built with **FastAPI, React, PostgreSQL, SQLAlchemy, Alembic, JWT Authentication, and Razorpay Test Mode**.

Features include product management, warehouse and inventory tracking, order processing, stock allocation, payment verification, and a responsive React frontend.

## Local setup (Windows)

### Option A — Docker Desktop (recommended)
1. Install and start Docker Desktop.
2. In this folder run `copy .env.example .env`.
3. Edit `.env`: set a long random `POSTGRES_PASSWORD`; make the password in `DATABASE_URL` match it; generate `JWT_SECRET_KEY` using `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
4. Start services: `docker compose up -d --build`.
5. Open Swagger: http://127.0.0.1:8000/docs
6. Check containers: `docker compose ps`; view API logs: `docker compose logs -f api`.

### Option B — Existing local PostgreSQL
1. Create and activate a virtual environment: `py -m venv venv` then `venv\Scripts\activate`.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `DATABASE_URL` for your local PostgreSQL server, plus a random `JWT_SECRET_KEY`.
4. Run migrations: `alembic upgrade head`.
5. Start API: `python -m uvicorn app.main:app --reload`.

## Local test commands

```cmd
python -m pip install -r requirements.txt
python -m pytest -q
```

The tests use isolated test configuration where possible. Run integration tests against a disposable test database; never point test runs at your real project database.

## Razorpay test mode (no real money)

1. In Razorpay dashboard, switch to **Test Mode** and create test API keys.
2. Put `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and a separate `RAZORPAY_WEBHOOK_SECRET` in `.env`.
3. Create an order through `POST /orders`.
4. Create a Razorpay payment order through authenticated `POST /orders/{order_id}/payments/razorpay`.
5. Complete Checkout in a test frontend and send the returned signature fields to `POST /payments/razorpay/verify`.
6. For webhook testing from a local machine, use a secure tunnel only if needed and configure the Razorpay webhook URL to that temporary endpoint. Never expose PostgreSQL or Redis.

Without Razorpay test credentials, the payment endpoints intentionally return `503`; the rest of the API remains usable.

## Optional AWS S3 testing (no deployment)

The API includes private S3 upload and short-lived download-link endpoints. This does **not** deploy the application to AWS. To test it: create a private S3 bucket in your chosen region; create a dedicated IAM identity limited to `s3:PutObject` and `s3:GetObject` on that bucket; configure credentials locally using the AWS CLI (`aws configure`) or environment variables; set `AWS_REGION` and `S3_BUCKET_NAME` in `.env`; restart the API. Then use authenticated `POST /files/s3` (multipart form field `file`, max 10 MB) and `GET /files/s3/download-url?key=uploads/<your-user-id>/...`. Users can generate download URLs only for their own uploaded objects. Objects remain private; download URLs expire after 5 minutes. Do not enable public bucket access. AWS may charge for requests and storage, so delete the test bucket/objects when finished and set an AWS Budget alert. Never put AWS access keys in Git or `.env.example`.

## Redis and Celery

Docker Compose starts local Redis and a Celery worker. Current worker contains a health-check task scaffold; business email/low-stock notification delivery is not implemented yet.

## Database migrations

Run `alembic upgrade head` for a new database. Existing databases should be backed up before migration. The latest migration adds exact order-to-inventory allocation records; orders created before that migration have no allocation history, so cancellation of those legacy orders is deliberately blocked rather than guessing which stock to restore.

## Security notes

- Never commit `.env`, credentials, database dumps, or real payment keys.
- Rotate any passwords or API secrets that were previously shared in chat.
- This is a portfolio/development project, not certified production software. Role-based authorization across all write endpoints, payment reconciliation, full integration/concurrency testing, email delivery, monitoring, rate limiting, backups, and security review remain required before real customer traffic.
