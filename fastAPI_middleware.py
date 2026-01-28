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
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )


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
