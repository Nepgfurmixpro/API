from fastapi import HTTPException, Request
from pydantic import BaseModel
import bcrypt
from models import User, without

class LoginUser(BaseModel):
    email: str
    password: str

async def login_user(req: Request, info: LoginUser):
    users = User.objects.filter(email=info.email)
    is_errored = False
    print(info.password)
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
    
    return without(dict(users[0]), {'password'})