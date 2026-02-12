import os

from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Ensure .env is available even if import order changes.
load_dotenv()


def _get_expected_api_key() -> str:
    api_key = os.getenv("TT4D_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server API key is not configured",
        )
    return api_key


async def api_key_auth(api_key: str = Security(api_key_header)):
    expected_api_key = _get_expected_api_key()

    if not api_key:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Missing API Key")
    if api_key != expected_api_key:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")
    return api_key
