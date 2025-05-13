import logging

# Configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

from fastapi import FastAPI

from app import routers

app = FastAPI()

app.include_router(routers.router)


@app.get("/")
async def root():
    return {"message": "TT4D API"}
