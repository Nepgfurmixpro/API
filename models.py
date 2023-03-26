from enum import Enum
import time
from cassandra.cqlengine.models import Model
from cassandra.cqlengine import columns
import re
from fastapi import HTTPException

from pydantic import BaseModel

from snowflake import EPOCH

BUCKET_SIZE = 1000 * 60 * 60 * 24 * 10

class User(Model):
    __table_name__ = 'users'

    id = columns.BigInt(primary_key=True)
    auth_token = columns.Text(index=True)
    avatar_hash = columns.Text()
    email = columns.Text(index=True)
    first_name = columns.Text()
    middle_initial = columns.Text()
    last_name = columns.Text()
    flags = columns.Integer()
    nickname = columns.Text()
    password = columns.Text()

    ignore_security = { 'password' }
    ignore_private = { 'auth_token' } | ignore_security
    ignore_personal = { 'email' } | ignore_private

class SchoolUser(Model):
    __table_name__ = 'school_users'

    school_id = columns.BigInt(primary_key=True)
    user_id = columns.BigInt(primary_key=True, index=True)
    flags = columns.Integer()
    permissions = columns.Integer()

class School(Model):
    __table_name__ = 'schools'

    id = columns.BigInt(primary_key=True)
    logo_url = columns.Text()
    name = columns.Text()
    owner_id = columns.BigInt()
    short_name = columns.Text()

class SchoolInvite(Model):
    __table_name__ = 'school_invites'

    user_id = columns.BigInt(primary_key=True)
    code = columns.Text(primary_key=True)
    school_id = columns.BigInt()

class Channel(Model):
    __table_name__ = 'school_channels'

    school_id = columns.BigInt(primary_key=True)
    channel_id = columns.BigInt(primary_key=True)
    parent_id = columns.BigInt()
    specialty_tag = columns.Text()
    type = columns.Integer()
    name = columns.Text()
    description = columns.Text()

class Message(Model):
    __table_name__ = 'messages'

    channel_id = columns.BigInt(partition_key=True)
    bucket = columns.BigInt(partition_key=True)
    message_id = columns.BigInt(primary_key=True, clustering_order='DESC')
    author_id = columns.BigInt(primary_key=True)
    content = columns.Text()

class APISchool(BaseModel):
    id: int
    logo_url: str | None
    name: str
    short_name: str | None
    owner_id: int
    owner: bool

def get_message_data(message: Message):
    users = User.objects.filter(id=message.author_id)
    if len(users) < 1:
        user = {}
    else:
        user = dict(users[0])

    return {
        'id': message.message_id,
        'author': without(user, User.ignore_personal),
        'content': message.content
    }

def without(d: dict, keys: dict):
    return {x: d[x] for x in d if x not in keys}

regex = r'\b(?:[a-z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])\b'

def validate_email(email: str):
    return re.fullmatch(regex, email)

def make_bucket(snowflake: int | None = None):
    if snowflake is None:
        timestamp = int(time.time() * 1000) - EPOCH
    else:
        timestamp = snowflake >> 22
    return int(timestamp / BUCKET_SIZE)

def make_buckets(start_id: int, end_id: int | None = None):
    return range(make_bucket(start_id), make_bucket(end_id) + 1)

def get_school_member(user: User, id: int) -> SchoolUser:
    users = SchoolUser.objects.filter(school_id=id, user_id=user.id)
    if len(users) < 1:
        raise HTTPException(status_code=401, detail={
            'message': 'Guild unavailable',
            'code': 40000
        })
    
    return users[0]

class SchoolMemberPermissions():
    MESSAGE_CREATE = 1 << 1
    MESSAGE_DELETE = 1 << 2
    CHANNEL_DELETE = 1 << 3
    CHANNEL_MODIFY = 1 << 4
    CHANNEL_CREATE = 1 << 5
    ROLE_ASSIGN = 1 << 6