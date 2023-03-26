from fastapi import HTTPException, Request
from pydantic import BaseModel
import bcrypt
from auth_token import create_token

from snowflake import create_snowflake

from models import User, validate_email, without

class CreateUser(BaseModel):
    first_name: str
    middle_initial: str | None
    last_name: str
    email: str
    password: str

async def create_user(req: Request, info: CreateUser):
    email = info.email

    if not validate_email(email):
        raise HTTPException(status_code=400, detail={
            'message': 'Invalid Form Body',
            'errors': {
                'email': {
                    'code': 'INVALID_EMAIL',
                    'message': 'Email is invalid'
                }
            },
            'code': 50000
        })

    if len(User.objects.filter(email=email)) > 0:
        raise HTTPException(status_code=400, detail={
            'message': 'Invalid Form Body',
            'errors': {
                'email': {
                    'code': 'EMAIL_TAKEN',
                    'message': 'Email already taken'
                }
            },
            'code': 50000
        })
    id = create_snowflake()
    password = bcrypt.hashpw(info.password.encode(), bcrypt.gensalt()).decode()
    user = User(**info.dict(exclude={ 'password' }), flags=0, id=id, password=password, auth_token=create_token(email, password, id))
    user.save()
    return without(dict(user), {'password'})