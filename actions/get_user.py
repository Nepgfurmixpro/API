from fastapi import HTTPException, Header, Request
from pydantic import BaseModel
import bcrypt
from auth_token import authorize
from models import User, without

async def get_user_self(authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    return without(user, { 'password', 'auth_token' })

async def get_user(id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    user = User.objects.filter(id=id)[0]
    return user