from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import admin, assistant, auth, dashboard, employees, payment, rules, transactions
from .seed import seed_defaults

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SplitPay API",
    description="Merchant-side payment-splitting assistant. QR generation, "
                 "configurable MDR rule engine, and transaction tracking.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "SplitPay API"}


app.include_router(auth.router)
app.include_router(payment.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)
app.include_router(rules.router)
app.include_router(admin.router)
app.include_router(employees.router)
app.include_router(assistant.router)
