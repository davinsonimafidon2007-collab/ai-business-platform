from fastapi import FastAPI, status


app = FastAPI(
    title="AI Business Platform API",
    description="API for the AI Business Platform.",
    version="0.1.0",
)


@app.get(
    "/health",
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
def get_health() -> dict[str, str]:
    return {"status": "operational"}
