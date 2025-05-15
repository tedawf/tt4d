import logging

# Configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)-7s] %(asctime)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

from fastapi import FastAPI

from app.routes.draw_router import router as draw_router
from app.routes.scrape_router import router as scrape_router

app = FastAPI(title="TT4D API")

app.include_router(draw_router, prefix="/draws")
app.include_router(scrape_router, prefix="/scrape")


@app.get("/")
async def root():
    return {"message": "Welcome to TT4D API"}
