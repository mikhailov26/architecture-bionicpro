import csv
import io
import os
import time
from datetime import date

import clickhouse_connect
import requests
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt

# ---------- Configuration ----------
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_PUBLIC_URL = os.getenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "reports-frontend")
REQUIRED_ROLE = os.getenv("REQUIRED_ROLE", "prothetic_user")

KEYCLOAK_CERTS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
KEYCLOAK_ISSUER = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"

CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CH_USER = os.getenv("CLICKHOUSE_USER", "admin")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "admin")
CH_DB = os.getenv("CLICKHOUSE_DATABASE", "default")

origins = [
    "http://localhost:3000",
    "https://frontend.architecture-bionicproo.orb.local",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()

# ---------- Keycloak certs cache ----------
_certs_cache = {"data": None, "ts": 0.0}

def get_certs():
    now = time.time()
    if _certs_cache["data"] and now - _certs_cache["ts"] < 3600:
        return _certs_cache["data"]
    resp = requests.get(KEYCLOAK_CERTS_URL, timeout=5)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch Keycloak keys")
    _certs_cache["data"] = resp.json()
    _certs_cache["ts"] = now
    return _certs_cache["data"]

def get_current_user(token: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    try:
        header = jwt.get_unverified_header(token.credentials)
        kid = header.get("kid")
        keys = get_certs()["keys"]
        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Public key not found")

        public_key = jwk.construct(key)
        payload = jwt.decode(
            token.credentials,
            public_key,
            algorithms=[key["alg"]],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
            options={"verify_aud": True, "verify_iss": True},
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    roles = payload.get("realm_access", {}).get("roles", [])
    if REQUIRED_ROLE not in roles:
        raise HTTPException(status_code=403, detail="Insufficient role")

    return payload

# ---------- ClickHouse helpers ----------
def get_ch_client():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT,
        username=CH_USER, password=CH_PASSWORD,
        database=CH_DB,
    )

def is_period_processed(period_end: date) -> bool:
    """Проверяет, что Airflow уже обработал данные до period_end включительно."""
    try:
        client = get_ch_client()
        row = client.query(
            "SELECT max(period_end) FROM reporting.processed_periods"
        ).first()
    except Exception:
        return False
    max_processed = row[0] if row and row[0] else None
    return max_processed is not None and period_end <= max_processed

def query_clickhouse(user_id: int, period_start: date, period_end: date):
    client = get_ch_client()
    result = client.query(
        """
        SELECT date, prosthesis_id, metric_type,
               avg_metric, min_metric, max_metric
        FROM reporting.reports_user_daily
        WHERE user_id = %(user_id)s
          AND date BETWEEN %(start)s AND %(end)s
        ORDER BY date
        """,
        {"user_id": user_id, "start": period_start, "end": period_end},
    )
    return result.result_rows

def extract_user_id(payload: dict) -> int:
    """user_id должен прийти из Keycloak user attribute 'user_id' (int)."""
    raw = payload.get("user_id")
    if raw is None:
        raise HTTPException(status_code=400, detail="user_id claim missing in token")
    return int(raw)

# ---------- Routes ----------
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/reports")
async def reports(
    period_start: date = Query(...),
    period_end: date = Query(...),
    user=Depends(get_current_user),
):
    if not is_period_processed(period_end):
        raise HTTPException(status_code=409, detail="Период ещё не обработан Airflow")
    user_id = extract_user_id(user)
    rows = query_clickhouse(user_id, period_start, period_end)
    return [
        {
            "date": r[0].strftime("%Y-%m-%d"),
            "prosthesis_id": r[1],
            "type": r[2],
            "avg_metric": r[3],
            "min_metric": r[4],
            "max_metric": r[5],
        }
        for r in rows
    ]

@app.get("/api/reports/download")
async def download_report(
    period_start: date = Query(...),
    period_end: date = Query(...),
    user=Depends(get_current_user),
):
    if not is_period_processed(period_end):
        raise HTTPException(
            status_code=409,
            detail="Данные за указанный период ещё не обработаны Airflow",
        )

    user_id = extract_user_id(user)
    rows = query_clickhouse(user_id, period_start, period_end)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["date", "prosthesis_id", "type", "avg_metric", "min_metric", "max_metric"]
    )
    for r in rows:
        writer.writerow([r[0].strftime("%Y-%m-%d"), r[1], r[2], r[3], r[4], r[5]])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="report.csv"'},
    )