import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN


API_KEY = os.getenv("TT4D_API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def api_key_auth(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Missing API Key")
    if api_key != API_KEY:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")
    return api_key
