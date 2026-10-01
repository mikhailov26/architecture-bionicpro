import os

import clickhouse_connect
import requests
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt

KEYCLOAK_URL = f"{os.getenv('KEYCLOAK_URL', 'http://localhost:8080')}"
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "reports-client")
CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "oNwoLQdvJAvRcL89SydqCWCe5ry1jMgq")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "reports-realm")
KEYCLOAK_ISSUER = f"localhost:8080/realms/{KEYCLOAK_REALM}"
KEYCLOAK_CERTS_URL = (
    f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
)

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


def get_certs():
    response = requests.get(KEYCLOAK_CERTS_URL)
    if response.status_code != 200:
        raise HTTPException(
            status_code=500, detail="Failed to fetch Keycloak public keys"
        )
    return response.json()


def get_current_user(token: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    print(token)
    try:
        unverified_header = jwt.get_unverified_header(token.credentials)
        kid = unverified_header.get("kid")

        keys = get_certs()["keys"]
        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            raise Exception("Public key not found")

        public_key = jwk.construct(key)

        payload = jwt.decode(
            token.credentials,
            public_key,
            algorithms=[key["alg"]],
            audience="reports-api",
        )

        roles = payload.get("realm_access", {}).get("roles", [])
        if "prothetic_user" not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")

        return payload

    except JWTError as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def query_clickhouse(user_id: int):
    client = clickhouse_connect.get_client(
        host="clickhouse", port=8123, username="admin", password="admin"
    )

    result = client.query(
        "SELECT date, prosthesis_id, metric_type, avg_metric, min_metric, max_metric FROM reports_user_daily WHERE user_id = %(user_id)s",
        {"user_id": user_id},
    )

    return result.result_rows


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/reports")
async def reports(user=Depends(get_current_user)):
    user_id = int(user["preferred_username"][-1])
    data = query_clickhouse(user_id)
    if not data:
        return []
    return [
        {
            "date": row[0].strftime("%Y-%m-%d"),
            "prosthesis_id": row[1],
            "type": row[2],
            "avg_metric": row[3],
            "min_metric": row[4],
            "max_metric": row[5],
        }
        for row in data
    ]