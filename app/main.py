from fastapi import FastAPI

from app import routers

app = FastAPI()

app.include_router(routers.router)


@app.get("/")
async def root():
    return {"message": "TT4D API"}
