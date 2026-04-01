from fastapi import FastAPI

from src.core.lifespan import lifespan

app = FastAPI(
    title="Kairos API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
