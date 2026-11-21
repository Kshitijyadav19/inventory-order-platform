# StockPilot React frontend

This folder is a React + Vite frontend for the existing FastAPI Inventory Order Management API.

## 1. Place the folder

Extract/copy this `frontend` folder into the root of your existing backend project:

```text
inventory-order-platform/
  app/
  migrations/
  tests/
  frontend/
    package.json
    vite.config.js
    index.html
    src/
```

## 2. Start FastAPI

Open CMD in the backend project root (the folder that contains `app`) and run:

```cmd
python -m uvicorn app.main:app --reload
```

FastAPI should be available at `http://127.0.0.1:8000`.

## 3. Start React

Open a SECOND CMD window in the backend project root and run:

```cmd
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally:

```text
http://127.0.0.1:5173
```

The Vite development proxy forwards `/api/*` requests to `http://127.0.0.1:8000/*`. You do not need to add CORS middleware for local development.

## Features

- Login and registration using the existing `/login` and `/register` endpoints
- Overview dashboard with products, stock, warehouses and order summaries
- Product catalog and create/delete
- Warehouse creation and listing
- Inventory creation, stock-in and stock-out
- Order creation, listing and cancellation
- Razorpay Checkout integration using the existing create-payment and verify-payment APIs
- Responsive layout for desktop and mobile

## Razorpay

The Pay action:
1. Calls `POST /orders/{order_id}/payments/razorpay`
2. Opens Razorpay Checkout using the returned `razorpay_key_id`, `razorpay_order_id`, amount and currency
3. Sends the Checkout response to `POST /payments/razorpay/verify`

Keep Razorpay secrets only in the backend `.env`. The frontend never reads or stores the Razorpay secret.

For test payments, use Razorpay Test Mode credentials and test payment details from your Razorpay Dashboard documentation.

## Notes

- This frontend is wired to the API response shapes in the current project bundle.
- If your local `app/main.py` has changed endpoint response field names, share the relevant endpoint response and the UI can be adjusted.
- The current backend has to permit the logged-in user to access the requested endpoints. The UI attaches the bearer token to API calls.
- AWS S3 upload UI can be added once the backend's upload/download response shape is confirmed.
