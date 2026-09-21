# SplitPay

**Split. Scan. Done.**

SplitPay is a merchant-side payment assistant. A merchant registers once,
saves their store name and UPI ID, and from then on only enters the
**total amount** a customer needs to pay. SplitPay analyzes the currently
configured UPI/MDR rules, splits the amount into installments, and
generates a separate UPI QR code for each installment for the customer to
scan with their own UPI app.

> **Important:** SplitPay is a payment-*planning* and QR-generation tool. It
> is not a tax-avoidance product, and splitting a payment does not guarantee
> that MDR or other charges will not apply. See [Legal / product framing](#legal--product-framing).

---

## 1. What's included

- **Backend** — FastAPI + SQLAlchemy, JWT auth, a configurable database-driven
  MDR rule engine, a split engine (standard / equal / custom), UPI QR
  generation, PDF receipts, transaction history, dashboard analytics, an
  admin rule-management API, employee accounts, and a data-grounded AI
  analytics assistant.
- **Frontend** — React + TypeScript + Tailwind CSS, mobile-first, installable
  as a PWA. Covers the full demo flow: register → dashboard → amount entry →
  payment analysis/split → QR carousel → mark received → receipt → history.
- **Database** — SQLAlchemy models designed for PostgreSQL in production;
  defaults to zero-setup SQLite for local development.

This is a working MVP built end-to-end and tested locally (see
[Demo flow](#11-verifying-the-demo-flow) below). Multi-branch analytics
consolidation and a fully wired admin *UI* (the admin *API* is complete) are
left as extension points — see [Extension points](#12-extension-points--whats-stubbed).

---

## 2. Project structure

```
splitpay/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, router wiring, CORS, startup seed
│   │   ├── config.py          # env-driven settings
│   │   ├── database.py        # SQLAlchemy engine/session
│   │   ├── models.py          # ORM models (merchants, rules, transactions, ...)
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── auth.py            # password hashing, JWT, role dependencies
│   │   ├── rules_engine.py    # configurable MDR rule matching
│   │   ├── split_engine.py    # standard/equal/custom installment splitting
│   │   ├── qr_service.py      # UPI URI + QR code generation
│   │   ├── receipt_service.py # PDF receipt generation
│   │   ├── seed.py            # seeds default categories/rules on first run
│   │   └── routers/           # auth, payment, transactions, dashboard, rules, admin, employees, assistant
│   ├── create_admin.py        # CLI to bootstrap an admin user
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.ts      # axios instance + auth interceptor
│   │   ├── context/AuthContext.tsx
│   │   ├── components/        # Layout (bottom nav), ProtectedRoute
│   │   ├── pages/              # Register, Login, Dashboard, AmountEntry,
│   │   │                       # Analysis, QR, Receipt, History, Rules,
│   │   │                       # Assistant, More (employees)
│   │   └── types/index.ts
│   ├── public/manifest.json, service-worker.js, icons/  # PWA
│   ├── Dockerfile, nginx.conf
│   └── package.json
├── database/migrations/       # placeholder for Alembic migrations (see §7)
├── docker-compose.yml
├── .env.example
└── README.md (this file)
```

---

## 3. Local installation (development)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate      # optional but recommended
pip install -r requirements.txt

cp ../.env.example .env         # uses SQLite by default — zero setup
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`. On first startup it auto-creates tables and
seeds the default merchant categories and the 2026 MDR rule set.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`.

### 3.1 Verifying the demo flow

1. Register a merchant (business name `ABC Store`, UPI ID `abcstore@upi`).
2. On the dashboard, enter `5000` and tap **Generate Payment QR**.
3. Confirm the analysis shows **Specified P2M above ₹2,000 → 0.4% MDR → ₹20.00 estimated**.
4. Confirm the standard split produces **₹2,000 / ₹2,000 / ₹1,000**.
5. Step through all 3 QR codes, tapping **Mark as Received** on each.
6. Confirm the completion screen, then view/download/print the receipt.
7. Confirm the transaction now appears in **History** and the dashboard's
   "Today's Sales" reflects it.

This exact flow was run against the backend during development and returns
the results above.

---

## 4. PostgreSQL setup (production database)

1. Create a database and user:
   ```sql
   CREATE DATABASE splitpay;
   CREATE USER splitpay_user WITH PASSWORD 'CHANGE_ME';
   GRANT ALL PRIVILEGES ON DATABASE splitpay TO splitpay_user;
   ```
2. Point the backend at it via `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql://splitpay_user:CHANGE_ME@localhost:5432/splitpay
   ```
3. Restart the backend — `Base.metadata.create_all()` creates all tables on
   startup. For ongoing schema changes in production, introduce Alembic
   migrations under `database/migrations/` (see §7).

---

## 5. Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | backend | SQLite (dev) or PostgreSQL (prod) connection string |
| `SECRET_KEY` | backend | JWT signing secret — set a long random value in production |
| `JWT_ALGORITHM` | backend | Defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | Session length |
| `AI_API_KEY` | backend | Optional; only needed if you extend the assistant to call an external LLM for phrasing (see `app/routers/assistant.py`) |
| `CORS_ORIGINS` | backend | Comma-separated list of allowed frontend origins |
| `VITE_API_BASE_URL` | frontend | Base URL the frontend calls; use `/api` when reverse-proxied together (see `docker-compose.yml` / `nginx.conf`) |

Copy `.env.example` → `.env` in each app and fill in real values. **Never
commit `.env` files** — `.gitignore` already excludes them.

---

## 6. GitHub upload

```bash
cd splitpay
git init
git add .
git commit -m "Initial SplitPay commit"
git branch -M main
git remote add origin https://github.com/<your-username>/splitpay.git
git push -u origin main
```

`.env`, `node_modules/`, `dist/`, and `*.db` files are already excluded via
`.gitignore` — double-check nothing secret is staged before your first push
(`git status`).

---

## 7. Database migrations

The app currently creates tables via `Base.metadata.create_all()` on
startup, which is fine for a first deployment but not for evolving a live
schema. For production schema changes, add [Alembic](https://alembic.sqlalchemy.org/):

```bash
cd backend
pip install alembic
alembic init ../database/migrations
# point alembic.ini's sqlalchemy.url at $DATABASE_URL, then:
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## 8. Production deployment

Recommended architecture:

```
User Mobile → HTTPS → Frontend (nginx/static) → FastAPI Backend → PostgreSQL
```

### Option A — Docker Compose (single VM / any Docker host)

```bash
cp .env.example .env    # fill in POSTGRES_PASSWORD, SECRET_KEY, CORS_ORIGINS
docker compose up -d --build
```

This starts PostgreSQL, the FastAPI backend, and an nginx-served frontend
build that reverse-proxies `/api/*` to the backend container.

### Option B — Render / Railway / Fly.io

1. **Database**: provision a managed PostgreSQL instance; copy its connection
   string into `DATABASE_URL`.
2. **Backend**: deploy `backend/` as a web service using its `Dockerfile`
   (or `pip install -r requirements.txt` + `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   as the start command). Set `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`.
3. **Frontend**: deploy `frontend/` as a static site — build command
   `npm run build`, publish directory `dist`. Set `VITE_API_BASE_URL` to your
   backend's public URL at build time.
4. Bootstrap an admin user once the backend is live:
   ```bash
   python create_admin.py --mobile 9000000000 --password "StrongPass123" --name "Admin"
   ```
   (run inside the backend container/instance, since there's no public
   admin-signup endpoint by design).

### Domain configuration & HTTPS

- Point your domain's DNS to your hosting platform (A/CNAME record per its
  instructions).
- Render/Railway/Fly.io all provision free HTTPS certificates automatically
  once a custom domain is attached.
- If self-hosting behind nginx (e.g. Docker Compose on a raw VM), terminate
  HTTPS with [Certbot](https://certbot.eff.org/) / Let's Encrypt in front of
  the `frontend` container, or place a load balancer with managed TLS in
  front of the whole stack.
- Set `CORS_ORIGINS` to your real HTTPS domain once deployed.

---

## 9. PWA installation

The frontend ships a `manifest.json`, a service worker (`public/service-worker.js`
— caches only the static app shell, never API/payment data or a fake
offline "success" state), and app icons. Once deployed over HTTPS:

1. Open the site on a phone.
2. Browser menu → **Add to Home Screen** (Android/Chrome) or **Share → Add to
   Home Screen** (iOS/Safari).
3. Launch SplitPay like a native app.

---

## 10. Security checklist

- [x] Passwords hashed with bcrypt (`passlib`), never stored in plaintext.
- [x] JWT-based session auth with configurable expiry.
- [x] Role-based access control (`owner`, `employee`, `admin`) via FastAPI
      dependencies.
- [x] Pydantic input validation on every request body.
- [x] SQL injection protection via SQLAlchemy's parameterized ORM queries
      (no raw string-interpolated SQL anywhere).
- [x] CORS restricted to configured origins (`CORS_ORIGINS`), not `*`.
- [x] Audit log table (`audit_logs`) for admin rule changes.
- [x] Never stores UPI PINs, OTPs, bank passwords, or card credentials —
      those are entered by the customer inside their own UPI app.
- [ ] **Rate limiting** — not yet wired in; add `slowapi` (or a reverse-proxy
      layer like nginx `limit_req`) in front of `/api/auth/*` before going
      live.
- [ ] **HTTPS** — enforced at the hosting/reverse-proxy layer (see §8), not
      inside the app itself.
- [ ] **Secrets** — `.env.example` documents required variables; set real
      values via your platform's secret manager, never commit `.env`.
- [ ] **CSRF** — this API is a pure JSON/Bearer-token API (no cookie-based
      session), which is inherently not CSRF-exposed the way cookie auth is;
      if you switch to cookie-based sessions, add CSRF tokens.

---

## 11. API reference (selected)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Register a merchant + owner account |
| POST | `/api/auth/login` | Log in, returns a JWT |
| POST | `/api/payment/analyze` | Estimate MDR for an amount |
| POST | `/api/payment/split` | Preview a split without creating a transaction |
| POST | `/api/payment/generate-qr` | Create a transaction + QR codes for each installment |
| POST | `/api/payment/{id}/mark-received` | Manual demo/MVP payment tracking |
| GET | `/api/payment/{id}/receipt.pdf` | Download the PDF receipt |
| GET | `/api/transactions` | Transaction history (filters: `period`, `search`, `status`) |
| GET | `/api/dashboard` | Merchant dashboard analytics |
| GET | `/api/rules` | Publicly viewable current MDR rules |
| POST/PUT/DELETE | `/api/admin/rules` | Admin-only rule management (requires `admin` role) |
| GET/POST | `/api/employees` | Owner-only employee management |
| POST | `/api/assistant/query` | AI analytics Q&A, grounded only in real transaction data |

Full interactive schema at `/docs` (Swagger UI) once the backend is running.

---

## 12. Extension points / what's stubbed

Built to spec and fully functional: registration, dashboard, amount entry +
calculator, rule analysis, standard/equal/custom split, QR generation and
carousel, manual payment tracking, PDF receipts, transaction history with
filters/search, the public rules page, employee create/deactivate, admin
rule CRUD, and a real-data-only AI assistant.

Designed for, with a simpler first cut so the core flow ships working:

- **Multi-branch consolidated analytics**: the `branches` table and
  per-transaction `branch_id` already exist; a merchant can have multiple
  branches with their own UPI IDs today, and generate-qr already accepts a
  `branch_id`. A dedicated cross-branch analytics rollup view is the natural
  next addition.
- **Payment-provider webhook**: `PaymentEvent` already models
  `source="webhook"` distinctly from manual tracking — wiring an actual
  payment aggregator's webhook to write `SUCCESS`/`FAILED` events is the
  next step for real (non-demo) payment confirmation. The app deliberately
  never fakes this.
- **AI assistant phrasing via an LLM**: the assistant currently answers
  directly from real query results (never inventing numbers). `AI_API_KEY`
  is wired through config if you want to add an LLM call purely to phrase
  the already-computed numbers more conversationally.

---

## Legal / product framing

- MDR (Merchant Discount Rate) is a **payment-system charge**, not a
  government tax — SplitPay never describes it as one, and never claims
  splitting a payment "avoids" it.
- Every screen that shows an MDR figure also shows the disclaimer: *"Applicable
  UPI/MDR treatment depends on the merchant category, transaction type,
  merchant status and current payment-network rules. Splitting a payment
  does not guarantee that MDR or other charges will not apply."*
- All MDR figures come from the `payment_rules` database table, not
  hard-coded application logic, and every rule carries an effective date and
  source reference, viewable on the **Rules** page.
- The app never disguises the true nature of a transaction or attempts to
  circumvent payment-network rules.
