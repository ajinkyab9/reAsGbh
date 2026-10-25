from fastapi import APIRouter, FastAPI

# Docs live under /api so they're reachable through the same routing
# in Vite dev, nginx (Docker) and Vercel.
app = FastAPI(
    title="Wind Forecast Monitor API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

api = APIRouter(prefix="/api")


@api.get("/health")
def health():
    return {"status": "ok"}


# include_router copies the routes registered so far, so keep this last.
app.include_router(api)
