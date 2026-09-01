# POWERLOOM — Full-Stack Commerce & Weaver Operations Platform

A recruiter-ready Django 5.2 marketplace for Indian powerloom sarees. The project combines customer commerce, inventory operations, order workflows, craft traceability, offers, reviews, notifications, analytics and PDF receipts in one coherent product.

## What is included

- Premium forest-green / ivory / muted-gold visual system
- Large editorial typography and responsive layouts
- Animated loom hero, reveal-on-scroll sections, hover depth, image sheen and loading states
- Customer registration/login and role-separated workshop access
- Product catalogue with search, category, fabric, colour, price and availability filters
- Wishlist / save-for-later interactions
- Product detail pages with provenance, weaver unit and traceability timeline
- Quantity-safe cart with stock limits
- Server-side `unit price × quantity` calculation
- Checkout with address capture, coupon validation and demo payment/COD workflow
- Transactional order creation with row-level stock locking
- Inventory ledger for sales, receipts, adjustments and cancellations
- Order status timeline and status history
- Customer notifications
- Verified-purchase reviews after delivery
- Admin dashboard with revenue, monthly revenue, sales trend and best sellers
- Catalogue management, inventory management, coupons and weaver management
- Downloadable PDF receipts
- PostgreSQL/Docker-ready configuration
- Automated regression tests for quantity/subtotal behaviour

## Local setup — Windows PowerShell

Use **`python -m pip`**, not `pip`, if Windows reports a broken `pip.exe` launcher.

```powershell
cd D:\Projects\powerloom\Powerloom_Final
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py bootstrap
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### Demo accounts

- Admin: `admin` / `admin12345`
- Customer: `customer` / `customer12345`

These credentials are for local presentation only. Change them before deployment.

### Important pricing rule

The project never trusts a browser-calculated total. Cart lines are rebuilt from the database, and checkout locks products, rechecks stock, reads the current unit price and calculates:

`line subtotal = current unit price × quantity`

`order subtotal = sum of all line subtotals`

`total = subtotal - valid discount + delivery + tax`

The unit price is then stored on each `OrderItem` so historical receipts remain stable even if catalogue prices change later.

## Docker

```powershell
docker compose up --build
```

## Project positioning for a resume

**Full-Stack Powerloom Commerce & Inventory Platform** — Django application implementing transactional cart/order processing, inventory ledgers, role-aware business operations, product traceability, coupons, reviews, notifications, analytics and production-ready configuration.
