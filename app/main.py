from fastapi import FastAPI, status

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)


@app.get(
    "/health",
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
def get_health() -> dict[str, str]:
    return {"status": "operational"}
