from fastapi import APIRouter, Depends, Request

from openhands.server.user_auth import get_user_auth
from openhands.server.user_auth.user_auth import UserAuth

app = APIRouter(prefix='/api')


@app.post('/authenticate')
async def authenticate(request: Request, user_auth: UserAuth = Depends(get_user_auth)):
    """
    Endpoint for frontend to verify authentication state.
    The dependency get_user_auth performs the validation (checking Bearer token).
    """
    user_id = await user_auth.get_user_id()
    # can return more info if needed
    return {'status': 'ok', 'user_id': user_id}


@app.post('/logout')
async def logout():
    """
    Logout endpoint for SaaS mode.
    With Bearer token auth (e.g. Entra), logout is client-side; this is a no-op
    for frontend compatibility.
    """
    return {}
