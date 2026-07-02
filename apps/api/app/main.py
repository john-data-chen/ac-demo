from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


# NestJS-compatible error shape: { statusCode, message, error }
def http_error(status_code: int, message: str, error: str):
    return JSONResponse(
        status_code=status_code,
        content={"statusCode": status_code, "message": message, "error": error},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return http_error(404, "Not Found", "Not Found")


# Register routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(boards_router.router)
app.include_router(projects_router.router)
app.include_router(tasks_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
