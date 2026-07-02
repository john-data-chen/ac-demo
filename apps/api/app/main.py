from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import auth as auth_router
from app.routers import boards as boards_router
from app.routers import projects as projects_router
from app.routers import tasks as tasks_router
from app.routers import users as users_router

app = FastAPI(title="Task Management API", version="1.0")

# CORS — mirrors NestJS config
allowed_origins = [
    settings.next_public_web_url,
    "https://turborepo-starter-kit-web.vercel.app",
    "http://localhost:3005",
    "http://localhost:8081",
    "http://localhost:19006",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Accept",
        "Authorization",
        "X-Requested-With",
        "X-XSRF-TOKEN",
        "Cookie",
    ],
    expose_headers=["Authorization", "XSRF-TOKEN", "Set-Cookie"],
)


# NestJS-compatible error shape: { statusCode, message, error } at top level
# (FastAPI default wraps everything in {"detail": ...}, which the web client can't read).
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        content = exc.detail
    else:
        phrase = HTTPStatus(exc.status_code).phrase
        content = {"statusCode": exc.status_code, "message": exc.detail, "error": phrase}
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)


# NestJS ValidationPipe returns 400 with a message array, not FastAPI's 422.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = [f"{'.'.join(str(x) for x in e['loc'][1:])}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(
        status_code=400,
        content={"statusCode": 400, "message": messages, "error": "Bad Request"},
    )


# Register routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(boards_router.router)
app.include_router(projects_router.router)
app.include_router(tasks_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
