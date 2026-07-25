from fastapi import FastAPI, status

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(users_router)


@app.get(
    "/health",
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
def get_health() -> dict[str, str]:
    return {"status": "operational"}
