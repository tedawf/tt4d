import logging

# Configure logging before anything else
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)-7s] %(asctime)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)

from dotenv import load_dotenv
from fastapi import FastAPI

from app.dddd.routes import draws_router as dddd_draws_router
from app.dddd.routes import jobs_router as dddd_jobs_router
from app.toto.routes import draws_router as toto_draws_router
from app.toto.routes import jobs_router as toto_jobs_router

# Load env once in whole app
load_dotenv()

app = FastAPI(title="TT4D API")

app.include_router(toto_draws_router)
app.include_router(toto_jobs_router)
app.include_router(dddd_draws_router)
app.include_router(dddd_jobs_router)


@app.get("/")
async def root():
    return {"message": "Welcome to TT4D API"}
