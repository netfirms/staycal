# StayCal — Homestay Room & Booking Management (Up-to-date Overview)

StayCal is a calendar-first, multi-tenant room management and booking web application designed for small homestays, guesthouses, and B&Bs. The philosophy is simplicity, affordability, and a powerful, visually-driven calendar interface. This README reflects the current implemented codebase and how to run and deploy it.

---

## 1. Business Idea & Value Proposition

- Problem: Small homestay owners often rely on cumbersome spreadsheets, paper calendars, or expensive, overly complex Property Management Systems (PMS). They need a simple, affordable, and centralized way to view room availability, manage bookings, and track guest information.
- Solution: StayCal provides a clean, calendar-first web application that focuses on booking management. It is built for low operational costs, enabling an affordable subscription model.
- Target Audience: Small hospitality operators (1–15 rooms): homestays, guesthouses, B&Bs, boutique inns.
- Monetization: Tiered monthly/annual subscriptions:
  - Free: 1 user, up to 2 rooms.
  - Basic: Up to 5 users, up to 10 rooms.
  - Pro: Unlimited users, unlimited rooms.

---

## 2. Current MVP Features (implemented)

- Public Landing Page
  - Marketing-style landing with hero, graphics, and CTAs to Register/Login.

- Authentication (session-based)
  - Register, Login, Logout.
  - Secure, server-signed cookie stored in the browser.

- Dashboard (/app)
  - Onboarding stepper to guide Homestay → Rooms → Booking.
  - Today’s operational widgets: incoming Check-ins and Check-outs for the active homestay.
  - FullCalendar per-room calendar with event colors by status and quick selection to create bookings.

- Calendar & Bookings
  - FullCalendar on the client, backed by a JSON events endpoint: GET /htmx/calendar/events.
  - Booking creation modal via HTMX: GET /htmx/booking/new (returns HTML fragment).
  - Save booking via HTMX: POST /htmx/booking/save (emits HX-Trigger bookingSaved to refresh calendars).
  - Prevents double-booking (overlap conflict detection per room).
  - Booking statuses: tentative, confirmed, checked_in, checked_out, cancelled.
  - Auto-checkout: any booking whose end_date is in the past is automatically set to checked_out on key views.

- Homestays (CRUD)
  - Owner creates/edits/deletes homestays.
  - Set active homestay for current session.

- Rooms (CRUD)
  - Manage rooms for the active homestay (name, capacity, default_rate).

- Bookings (CRUD)
  - Create, edit, delete bookings; overlap conflicts prevented.
  - Price and all money values displayed as THB with thousand separators (e.g., ฿1,234.00).

- Overview (/app/overview)
  - Stats per homestay: nights, bookings count, profit (sum of booking prices), rooms count.
  - Today’s counts per homestay: Check-ins Today, Check-outs Today.
  - Upcoming Check-ins list for the active homestay.
  - Period-based stats filter (start/end). Defaults to current month if no period provided.

- Admin
  - /admin shows lists of Users, Homestays, Subscriptions for admin users.
  - /admin/plans lets admins assign or update a user's subscription (plan, status, expiry).

---

## 3. High-Level Architecture

- Frontend: HTML5 + Tailwind CSS. Interactivity via HTMX for partial HTML updates and FullCalendar for the dashboard calendar UI.
- Backend: Monolithic FastAPI service handling auth, business logic, DB access, and Jinja2 template rendering.
- Database: SQLAlchemy ORM. Defaults to SQLite locally; supports PostgreSQL in production (Railway).
- Deployment: Dockerized; designed to run on Railway with a managed PostgreSQL.

Mermaid diagram:

```mermaid
flowchart LR
  subgraph Client
    A[Browser\nHTML + CSS + HTMX + FullCalendar]
  end

  subgraph Railway[Railway Deployment]
    subgraph App[FastAPI Monolith]
      B[FastAPI Routers\n- public_views\n- auth_views\n- app_views\n- rooms_views\n- bookings_views\n- homestays_views\n- calendar_htmx_views\n- admin_views]
      C[Jinja2 Templates\nSSR + HTMX partials]
      D[Security\nSession cookie]
      E[SQLAlchemy ORM]
      G[Auto-Checkout Service]
    end

    F[(PostgreSQL / SQLite)]
  end

  A -- HTMX GET/POST --> B
  A -- FullCalendar events JSON --> B
  B -- Render --> C
  B -- Query/Commit --> E
  E -- Connection --> F
  B -- trigger --> G
```

---

## 4. Detailed Architecture & Routes

- Web Framework: FastAPI
- Server: Uvicorn
- Templates: Jinja2
- Interactivity: HTMX 1.9+ and FullCalendar 6.x via CDN
- ORM: SQLAlchemy 2.0 (tables auto-created on app startup for MVP)
- Auth: Session cookie via itsdangerous

Key routers/endpoints:
- public_views
  - GET / → Landing page
- auth_views
  - GET /auth/login, POST /auth/login
  - GET /auth/register, POST /auth/register
  - POST /auth/logout
- app_views
  - GET /app → Dashboard (today’s ops, per-room calendars)
  - GET /app/overview → Stats and listings, with optional ?start=YYYY-MM-DD&end=YYYY-MM-DD; defaults to current month
- calendar_htmx_views
  - GET /htmx/booking/new → Booking modal (HTML fragment)
  - POST /htmx/booking/save → Create booking; emits HX-Trigger: bookingSaved
  - GET /htmx/calendar/events → JSON events for FullCalendar
  - POST /htmx/booking/update-status → Update booking status
- homestays_views
  - /app/homestays/ (list/create), edit, delete, set-active
- rooms_views
  - /app/rooms/ (list/create), edit, delete
- bookings_views
  - /app/bookings/ (list), new/create, edit/update, delete
- admin_views
  - GET /admin/ (basic admin dashboard; requires role=admin)

Auto-checkout integration:
- Executed on key requests (dashboard, overview, bookings list, calendar view) to mark past end_date bookings as checked_out.

---

## 5. Data Structure and Relations

Core tables and fields:

- users
  - id (PK)
  - email (UNIQUE)
  - hashed_password
  - role (admin | owner | staff)
  - homestay_id (FK → homestays, NULL for admin)
  - created_at (timestamp)

- subscriptions
  - id (PK)
  - owner_id (FK → users, UNIQUE)
  - plan_name (free | basic | pro)
  - status (active | cancelled | expired)
  - expires_at (timestamp)

- homestays
  - id (PK)
  - owner_id (FK → users)
  - name
  - address
  - created_at (timestamp)

- rooms
  - id (PK)
  - homestay_id (FK → homestays)
  - name
  - capacity (integer)
  - default_rate (decimal)

- bookings
  - id (PK)
  - room_id (FK → rooms)
  - guest_name
  - guest_contact
  - start_date (date)
  - end_date (date)
  - price (decimal)
  - status (tentative | confirmed | checked_in | checked_out | cancelled)

Relationships:

- Owner user has one or more Homestays and one Subscription.
- Homestay has many Rooms and many Users (staff via users.homestay_id).
- Room has many Bookings.

Mermaid ER diagram:

```mermaid
erDiagram
  USERS ||--o{ HOMESTAYS : owns
  USERS ||--o{ SUBSCRIPTIONS : has
  HOMESTAYS ||--o{ ROOMS : contains
  HOMESTAYS ||--o{ USERS : staff_of
  ROOMS ||--o{ BOOKINGS : has

  USERS {
    id int PK
    email varchar
    hashed_password varchar
    role varchar
    homestay_id int
    created_at timestamp
  }
  SUBSCRIPTIONS {
    id int PK
    owner_id int
    plan_name enum
    status enum
    expires_at timestamp
  }
  HOMESTAYS {
    id int PK
    owner_id int
    name varchar
    address varchar
    created_at timestamp
  }
  ROOMS {
    id int PK
    homestay_id int
    name varchar
    capacity int
    default_rate decimal
  }
  BOOKINGS {
    id int PK
    room_id int
    guest_name varchar
    guest_contact varchar
    start_date date
    end_date date
    price decimal
    status enum
  }
```

Booking conflict rule:

```
For a given room_id, (start_date, end_date) of any two bookings must not overlap.
```

---

## 6. Technology Stack

- Python 3.10+
- FastAPI + Uvicorn
- SQLAlchemy 2.0
- PostgreSQL (production) / SQLite (local default)
- Jinja2 templates
- HTMX 1.9+
- FullCalendar 6.x (via CDN)
- Tailwind CSS (via CDN)
- passlib[bcrypt] with bcrypt==4.0.1 (pinned for compatibility)

Key pinned dependencies (see requirements.txt):
- fastapi==0.118.0
- uvicorn[standard]==0.30.6
- sqlalchemy==2.0.34
- psycopg[binary]==3.2.10
- python-multipart==0.0.20
- passlib[bcrypt]==1.7.4
- bcrypt==4.0.1
- python-dotenv==1.0.1
- itsdangerous==2.2.0

---

## 7. Local Development

Quick start with the helper script:

```
bash run_local.sh
```

What it does:
- Creates .venv if missing and installs requirements.
- Copies .env.example to .env if missing.
- Exports DEBUG=true and runs the app at http://127.0.0.1:8000 with reload.
- Uses SQLite staycal.db by default unless DATABASE_URL is set.

Manual steps (alternative):
- Create venv, install requirements, set env, run:

```
uvicorn app.main:app --reload
```

Environment variables (.env):
- SECRET_KEY=change-me
- SESSION_COOKIE_NAME=staycal_session
- DATABASE_URL=postgresql+psycopg://user:password@host:port/dbname (omit to use SQLite)

Initial user journey:
- Visit / → click Register to create an account.
- Go to /app/homestays/ → create a Homestay and set it active.
- Go to /app/rooms/ → add rooms (optionally set default_rate).
- Go to /app → use the calendar to select dates and create bookings.
- Manage Bookings at /app/bookings/; edit status, dates, price, etc.

---

## 8. Deployment on Railway

- Dockerfile provided; service listens on PORT (default 8000).
- Steps:
  1. Create a PostgreSQL service on Railway.
  2. Create a service from this repository (Dockerfile build).
  3. Set environment variables in Railway:
     - DATABASE_URL (provided automatically by Railway’s Postgres plugin)
     - SECRET_KEY (set a strong value)
     - SESSION_COOKIE_NAME (optional)
  4. Deploy; Railway will assign a public domain.

Dockerfile entrypoint:

```
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
```

---

## 9. Notes & Limitations (MVP)

- Tables are auto-created on startup (Base.metadata.create_all). Use Alembic migrations for production changes.
- No payment gateway is implemented; subscriptions are modeled but not enforced.
- Admin panel is minimal and intended for demonstration/testing.
- Email/notifications are not implemented.
- Session cookies are not marked secure in DEBUG; set secure cookies behind HTTPS in production.

---

## 10. Changelog (recent highlights)

- Replaced custom month grid with FullCalendar on the dashboard; added JSON events endpoint.
- Implemented Homestay, Room, and Booking CRUD.
- Added Overview with period-based stats (defaults to current month), THB currency formatting, today’s check-ins/outs, upcoming check-ins list.
- Implemented auto-checkout of past-end-date bookings on key pages.
- Added public landing page with graphics and CTAs.
- Fixed dependencies and compatibility (psycopg[binary], python-multipart, bcrypt pin) and removed incorrect htmx pip dep.
- Added run_local.sh helper and .env.example.

---

## 11. License

Add your preferred open-source license here.

## 6. Minimal Technology Stack

- Backend Language: Python 3.10+
- Web Framework: FastAPI with Uvicorn
- Database: PostgreSQL
- ORM: SQLAlchemy 2.0 + Alembic
- Frontend Interactivity: HTMX 1.9+
- CSS Framework: Tailwind CSS (utility-first)
- Templating: Jinja2
- Authentication: passlib + bcrypt for password hashing

---

## 7. Deployment on Railway

1. Project Structure: Single Git repository containing the Python app.
2. Dockerfile:
   - Base image: python:3.10-slim (or newer compatible).
   - Set working directory, install dependencies from requirements.txt.
   - Expose port and run with Uvicorn.
   - Example CMD: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Railway Services:
   - Provision PostgreSQL from the Railway marketplace.
   - Create a new service connected to this repo (with Dockerfile).
4. Environment Variables:
   - Railway injects `DATABASE_URL` automatically; the app must read it.
   - Add `SECRET_KEY`, `SESSION_COOKIE_NAME`, and any other required settings.
5. Build & Deploy:
   - Push to the main branch to trigger build and deploy.
   - Railway provides a public domain for access.

---

## Getting Started (Local Development)

1. Prerequisites
   - Python 3.10+
   - PostgreSQL 13+
   - Node (optional) if building Tailwind locally

2. Setup
   - Create and activate a virtualenv.
   - `pip install -r requirements.txt`
   - Configure `.env` (DATABASE_URL, SECRET_KEY, etc.).
   - Initialize DB: `alembic upgrade head`.

3. Run
   - `uvicorn app.main:app --reload`
   - Open http://localhost:8000

---

## Security & Privacy Notes

- Use HTTPS in production (Railway + custom domain/SSL).
- Hash passwords with bcrypt via passlib; never store plaintext.
- Use secure, HttpOnly, SameSite cookies for session.
- Enforce tenant isolation at query level (filter by homestay_id for owners/staff).

---

## Roadmap (Post-MVP)

- Payment gateway integration (Stripe) for self-serve plan management.
- iCal export/import; channel manager integrations.
- Reporting and analytics (occupancy, revenue, ADR).
- Bulk actions on calendar; drag-and-drop booking edits.
- Email/SMS notifications and reminders.

---

## License

Copyright © 2025. All rights reserved. Update with your chosen license.


---

## 12. Monetization Strategy & Pricing (Detailed)

This section outlines a sustainable, flexible monetization model for StayCal that fits small homestays and scales as they grow. It includes pricing tiers, add‑ons, usage limits and overages, billing operations, regional pricing (THB‑first), trials/discounts, plan enforcement, and success metrics.

### 12.1 Pricing Model Overview

- Core model: Subscription (monthly/annual) with plan‑based feature gates and limits.
- Primary value axes:
  - Rooms (inventory size and operational complexity)
  - Seats (number of users/staff)
  - Advanced features (automation, integrations, reporting)
- Secondary monetization: Add‑ons (charged per property/tenant), usage‑based overages for optional services.

Mermaid plan ladder (overview):

```mermaid
flowchart TB
  A[Free] --> B[Basic]
  B --> C[Pro]
  click A "#free-tier-details" "Free tier details"
  click B "#basic-tier-details" "Basic tier details"
  click C "#pro-tier-details" "Pro tier details"

  subgraph Features by tier
  direction LR
  F1[Rooms Limit]:::f --> F2[Seats Limit]:::f --> F3[Calendar + HTMX]:::f --> F4[Conflict Detection]:::f --> F5[FullCalendar UI]:::f
  F6[Overview / Period Stats]:::p --> F7[Auto-Checkout]:::p --> F8[Export/Reports]:::p
  F9[Integrations / iCal]:::pro --> F10[API Access]:::pro --> F11[Priority Support]:::pro
  end

  classDef f fill:#eef,stroke:#88f,color:#124;
  classDef p fill:#efe,stroke:#6b6,color:#143;
  classDef pro fill:#ffe,stroke:#cc4,color:#432;
```

### 12.2 Tiered Plans

#### Free Tier (anchor)  <a id="free-tier-details"></a>
- 1 user, up to 2 rooms.
- Core calendar with conflict detection and booking CRUD.
- Auto‑checkout and today’s operations widgets.
- Community support only.
- Purpose: frictionless onboarding; showcase core value.

#### Basic Tier  <a id="basic-tier-details"></a>
- Up to 5 users, up to 10 rooms.
- Everything in Free, plus:
  - Full Overview with current‑month default period stats.
  - CSV export (bookings, rooms) and simple monthly report.
  - Email support (best‑effort).
- Suggested pricing (example):
  - THB 249/month or THB 2,490/year (2 months free).

#### Pro Tier  <a id="pro-tier-details"></a>
- Unlimited users and rooms.
- Everything in Basic, plus:
  - iCal export (per‑room), manual import (MVP) with dedupe rules.
  - Upcoming arrivals dashboard and occupancy KPIs.
  - Priority support (response‑time target) and onboarding assistance.
- Suggested pricing (example):
  - THB 699/month or THB 6,990/year.

Note: Exact pricing should be validated by interviews and willingness‑to‑pay tests; keep regional purchasing power in mind.

### 12.3 Add‑ons (Optional upsells)
- SMS notifications (per message, usage‑based; country‑specific rates).
- WhatsApp / LINE notifications (per message or monthly bundle).
- Branded PDF reports (per homestay, monthly add‑on).
- Multi‑property portfolio view (if owner manages 2+ properties) — flat monthly.
- Channel sync (future) — priced per connected channel.

### 12.4 Usage Limits and Overage Strategy
- Free limits enforced strictly; Basic/Pro enforce soft limits with warnings before hard cap.
- Optional overage for message‑based add‑ons (pay‑as‑you‑go) with prepaid bundles to avoid surprise bills.
- Clear UI indicators when nearing plan limits (e.g., 80% of rooms/seats limit).

### 12.5 Billing, Trials, and Discounts
- Billing provider: Stripe (recommended) for subscriptions, proration, invoices, and dunning.
- Trials: 14‑day trial on Basic/Pro (no card initially for MVP; card‑required can be A/B tested later).
- Coupons/Discounts: Intro offers, annual prepay discount (~16–20%), nonprofit/education discounts on request.
- Proration: mid‑cycle upgrade charges prorated automatically; downgrades effective next cycle by default.
- Invoicing: Email receipts; downloadable invoices inside the app (owner only).
- Dunning: Stripe Smart Retries + email reminders; downgrade to Free after grace period if payment fails.

Mermaid billing lifecycle:

```mermaid
flowchart LR
  U[User selects plan] --> T{Trial?}
  T -- yes --> TR[Start trial]
  T -- no --> S[Start paid subscription]
  TR --> A[Trial end]
  A --> |auto-convert| S
  S --> B{Payment success?}
  B -- yes --> ACT[Active]
  B -- no --> DNG[Dunning & Retries]
  DNG --> |recover| ACT
  DNG --> |fail grace| DWN[Auto downgrade to Free]
```

### 12.6 Plan Enforcement (Product side)
- Authentication/Authorization:
  - Plan and limits attached to tenant (homestay owner).
  - Staff inherit owner’s plan limitations.
- Enforcement examples:
  - Room creation blocked beyond plan limit (with upgrade CTA).
  - Seat invitations blocked beyond plan limit.
  - Features behind flags (e.g., iCal export only on Pro).
- Grace behaviors:
  - Read‑only access to over‑limit data after downgrade.
  - Continue calendar view, but block new booking creation if critical limits exceeded (configurable).

### 12.7 Metrics & Analytics
- Core SaaS metrics: MRR, Churn, LTV, ARPU, CAC (track via Stripe data + internal events).
- Product metrics: activation rate (Homestay → Room → Booking), time‑to‑value, monthly active properties.
- Expansion revenue: upsell adoption (Pro, Add‑ons), average rooms per tenant growth.
- Instrument events (page views, CRUD actions, upgrades) with a lightweight analytics tool; ensure GDPR/PDPA compliance.

### 12.8 Go‑to‑Market Levers
- Self‑serve onboarding with Free tier + in‑product upgrade prompts.
- Referral program: 1 free month for referrer + referee after first paid month.
- Partnerships: local tourism boards, homestay associations; offer group discounts.
- Content/SEO: “homestay booking calendar template”, “B&B calendar PMS” guides.

### 12.9 Regional Pricing and Currency
- Default display currency: THB; support multi‑currency pricing tables via Stripe Prices.
- Localized tax handling (VAT) via Stripe Tax when expanding regions.
- Accept local payment methods where possible for conversion uplift.

### 12.10 Operational Notes (MVP → Production)
- Begin with manual plan assignment (admin) while payments are wired up.
- Introduce Stripe Checkout + Customer Portal for self‑serve upgrades/downgrades.
- Background job to sync subscription status (webhooks) and enforce in app.
- Maintain a changelog of plan/limit changes per tenant for support/audit.

Mermaid system interaction (payments):

```mermaid
sequenceDiagram
  participant U as User (Owner)
  participant SC as StayCal App
  participant ST as Stripe
  U->>SC: Upgrade to Pro
  SC->>ST: Create Checkout Session (price_id, customer)
  ST-->>U: Hosted Checkout
  U-->>ST: Payment details
  ST-->>SC: Webhook: checkout.session.completed
  SC->>SC: Activate Pro plan, update limits
  SC-->>U: Confirmation (Pro active)
  ST-->>SC: Webhook: invoice.payment_failed (later)
  SC->>SC: Start dunning, set grace window
```

### 12.11 Example Pricing Summary (Draft)
- Free: 1 user, 2 rooms. ฿0. Always free.
- Basic: 5 users, 10 rooms. ฿249/mo or ฿2,490/yr.
- Pro: Unlimited users & rooms. ฿699/mo or ฿6,990/yr.
- Add‑ons: SMS/WhatsApp notifications (usage‑based), Branded Reports, Portfolio View, Channel Sync (future).

> Note: All prices are placeholders for illustration; validate with local market research and adjust.


---

## 13. To‑Do: Interesting Feature Ideas

These are high‑leverage, user‑visible enhancements we’re considering post‑MVP. They complement (not duplicate) the existing Roadmap and Monetization sections.

- Seasonal Pricing & Rate Plans
  - Define seasons, weekend/weekday rules, and per‑room overrides; visualize rates on a mini rate calendar.
- Extras, Packages, and Line‑Items
  - Add optional upsells to a booking (breakfast, airport pickup, tours), auto‑sum totals, and include in reports.
- Housekeeping & Turnover Board
  - Auto‑generate cleaning tasks between stays, assign to staff, track statuses (To Do / In Progress / Done).
- Smart Room Assignment (Optimization)
  - Suggest the best room for a new booking to minimize gaps and maximize occupancy; offer alternatives if conflicts.
- Maintenance & Blackout Dates
  - Block rooms for maintenance with notes and attachments; reflect blocks on calendars and in availability APIs.
- Guest CRM & Loyalty
  - Profiles with stay history, tags, notes; quick rebook; PDPA/GDPR export; optional loyalty tiers.
- Digital Pre‑Check‑in
  - Pre‑arrival form, ID/photo upload, e‑signature for registration card; automate status transition to checked_in.
- PWA & Offline Mode
  - Installable web app with cached dashboards; queue actions while offline and sync when back online.
- Multi‑language (i18n) & Locale Support
  - UI translations (TH/EN first), localized dates/currency formats, right‑to‑left readiness where applicable.
- Two‑Way Calendar Sync (Extended)
  - Robust iCal/OTA two‑way sync with dedupe, conflict resolution UI, and background jobs.
- Notifications Hub
  - WhatsApp/LINE/SMS/email templates; triggers for reminders, upcoming arrivals, overdue check‑outs.
- Webhooks & Public API
  - Outbound webhooks for booking/room events; API keys per tenant with scopes; simple REST endpoints.
- Advanced Analytics
  - Occupancy, ADR, RevPAR, pickup/pace; channel mix; export as CSV/PDF with branded templates.
- Accounting Exports
  - Xero/QuickBooks CSV exports; basic mapping of revenue categories and taxes.
- Roles & Permissions Matrix
  - Granular capabilities beyond owner/staff (e.g., housekeeping, front desk); audit trail of critical changes.
- Bulk Calendar Operations (Enhanced)
  - Multi‑select move/cancel; resize bookings in FullCalendar; keyboard shortcuts for power users.
- Print & Share
  - PDF calendar snapshots and shareable read‑only links for owners/partners.
- Dark Mode & Theming
  - Per‑user theme preference with accessible color palettes; auto respect system dark mode.

> Note: Items above are candidate ideas. Prioritization will be informed by user feedback, support volume, and impact on activation/retention.
