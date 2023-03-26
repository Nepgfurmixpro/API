from fastapi import APIRouter, HTTPException, Header, Request
import bcrypt
from pydantic import BaseModel
from auth_token import authorize, create_token
from cassandra.cqlengine.query import BatchQuery

from snowflake import create_snowflake

from models import APISchool, School, SchoolUser, User, validate_email, without


router = APIRouter(prefix='/users')

@router.get('/@me')
async def get_user_self(authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    return without(user, User.ignore_private)

@router.get('/@me/schools')
async def get_user_self(authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    schools: set[SchoolUser] = SchoolUser.objects.filter(user_id=user.id)
    school_ids = []
    for school in schools:
        school_ids.append(school.school_id)
    
    out = []

    for id in school_ids:
        school = School.objects.filter(id=id)
        if len(school) > 0:
            out.append(APISchool(**dict(school[0]), owner=school[0].owner_id == user.id))
    return out

@router.get('/{id}')
async def get_user(id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    users = User.objects.filter(id=id)
    if len(users) < 1:
        raise HTTPException(status_code=400, detail={
            'message': 'User not found',
            'code': 4030
        })
    out = without(users[0], User.ignore_personal)
    flags = out.pop('flags')
    out['public_flags'] = flags & 0xffffff
    return out
