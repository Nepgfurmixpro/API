from fastapi import APIRouter, HTTPException, Request
import bcrypt
from pydantic import BaseModel
from auth_token import create_token

from snowflake import create_snowflake

from models import User, validate_email, without


router = APIRouter(prefix='/auth')

class CreateUser(BaseModel):
    first_name: str
    middle_initial: str | None
    last_name: str
    email: str
    password: str

@router.post('/users/create')
async def create_user(req: Request, info: CreateUser):
    email = info.email.lower()

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
    return without(dict(user), User.ignore_security)

class LoginUser(BaseModel):
    email: str
    password: str

@router.post('/users/login')
async def login_user(req: Request, info: LoginUser):
    users = User.objects.filter(email=info.email)
    is_errored = False
    if len(users) < 1:
        is_errored = True
    if not is_errored and not bcrypt.checkpw(info.password.encode(), users[0].password.encode()):
        is_errored = True

    if is_errored:
        raise HTTPException(status_code=400, detail={
            'message': 'Invalid Form Body',
            'errors': {
                'email': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Email/Password is incorrect'
                },
                'password': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Email/Password is incorrect'
                }
            },
            'code': 50000
        })
    
    return without(dict(users[0]), User.ignore_security)