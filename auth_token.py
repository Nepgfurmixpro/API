import hmac
import base64
import hashlib
from datetime import datetime

from fastapi import HTTPException

from models import User

def create_token(email: str, password: str, id: int):
    key: hmac.HMAC = hmac.new(password.encode(), b'', hashlib.sha256)
    key.update(email.encode())
    key.update(id.to_bytes(64))
    idhash = str(base64.b64encode(str(id).encode()), encoding='utf-8').replace('=', '')
    timestamphash = str(
                    base64.b64encode(
                    str(int(datetime.now().timestamp())).encode()), encoding='utf-8').replace('=', '')
    hmachash = str(base64.urlsafe_b64encode(key.digest()), encoding='utf-8').replace('=', '')
    return f'{idhash}.{timestamphash}.{hmachash}'

def verify_token(token: str, id: int):
    split = token.split('.')
    id_dec = int(base64.b64decode(split[0] + '=='))
    ts_dec = int(base64.b64decode(split[1] + '=='))
    id_timestamp = id >> 22
    if ts_dec < id_timestamp:
        return False
    if id_dec != id:
        return False
    return True

def authorize(token: str | None):
    if token == None:
        raise HTTPException(status_code=401, detail={
            'message': 'Unauthorized',
            'code': 0
        })
    
    users = User.objects.filter(auth_token=token)
    if len(users) < 1:
        raise HTTPException(status_code=401, detail={
            'message': 'Unauthorized',
            'code': 0
        })
    
    user: User = users[0]
    return user
