from fastapi.responses import Response, JSONResponse
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def log_request_response(request: Request, call_next):
    start_time = time.time()

    # ---- Get client IP ----
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0]
    else:
        client_ip = request.client.host if request.client else "unknown"

    # ---- Read request body ----
    request_body = await request.body()
    try:
        request_body = request_body.decode("utf-8")
    except Exception:
        request_body = str(request_body)

    # ---- Process request ----
    response = await call_next(request)

    # ---- Read response body ----
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    process_time = round(time.time() - start_time, 4)

    # ---- Logging ----
    print("----- API LOG -----")
    print(f"Client IP    : {client_ip}")
    print(f"Method       : {request.method}")
    print(f"URL          : {request.url.path}")
    print(f"Request Body : {request_body}")
    print(f"Status Code  : {response.status_code}")
    print(f"Response Body: {response_body.decode('utf-8')}")
    print(f"Time Taken   : {process_time}s")
    print("-------------------")

    # ---- Recreate response (important!) ----
    # this will can cause if request are too much not memory efficient
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )

# decorators to log response is recommended way 
from functools import wraps
from fastapi import Request

from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    action = Column(String(100), index=True)
    resource_id = Column(String(100))
    status = Column(String(20))
    ip = Column(String(45))
    request_id = Column(String(36))
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

def log_audit(
    db,
    user_id: int,
    action: str,
    resource_id: str = None,
    status: str = "SUCCESS",
    ip: str = None,
    request_id: str = None,
    metadata: dict = None,
):
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_id=resource_id,
        status=status,
        ip=ip,
        request_id=request_id,
        metadata=metadata,
    )
    db.add(audit)
    db.commit()


def audit_log(action: str, resource_key: str = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request")
            db = kwargs.get("db")

            user_id = getattr(request.state, "user_id", None)

            try:
                response = await func(*args, **kwargs)
                status = "SUCCESS"
                return response

            except Exception as e:
                status = "FAILED"
                raise e

            finally:
                if db and request:
                    log_audit(
                        db=db,
                        user_id=user_id,
                        action=action,
                        resource_id=kwargs.get(resource_key) if resource_key else None,
                        status=status,
                        ip=request.client.host if request.client else None,
                        request_id=request.headers.get("X-Request-ID"),
                    )
        return wrapper
    return decorator

@app.post("/users/{user_id}")
@audit_log(action="USER_UPDATED", resource_key="user_id")
async def update_user(
    user_id: int,
    request: Request,
    db=Depends(get_db)
):
    return {"status": "updated"}


# Using dependancy
from fastapi import Depends, Request

def audit_dependency(action: str):
    async def dependency(
        request: Request,
        db=Depends(get_db)
    ):
        yield
        log_audit(
            db=db,
            user_id=request.state.user_id,
            action=action,
            ip=request.client.host if request.client else None,
            request_id=request.headers.get("X-Request-ID"),
        )
    return dependency

@app.post(
    "/profile",
    dependencies=[Depends(audit_dependency("PROFILE_UPDATED"))]
)
async def update_profile():
    return {"status": "ok"}

@app.get("/users")
def get_users():
    dummy_data = [
        {
            "id": 1,
            "name": "Rajesh",
            "role": "Full Stack Developer"
        },
        {
            "id": 2,
            "name": "Amit",
            "role": "Backend Developer"
        }
    ]

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Users fetched successfully",
            "data": dummy_data
        }
    )
