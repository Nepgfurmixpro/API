from random import randrange
from fastapi import APIRouter, HTTPException, Header, Request
import bcrypt
from pydantic import BaseModel
from auth_token import authorize, create_token
from cassandra.cqlengine.query import BatchQuery

from snowflake import create_snowflake

from models import APISchool, Channel, Message, School, SchoolInvite, SchoolMemberPermissions, SchoolUser, User, get_message_data, get_school_member, make_bucket, validate_email, without
from database import pika_channel

router = APIRouter(prefix='/schools')

@router.put('/join/{code}')
def join_school(code: str, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    invites = SchoolInvite.objects.filter(email=user.email, code=code)
    invite: SchoolInvite | None = None
    if len(invites) > 0:
        invite = invites[0]
    if invite != None:
        school = invite.school_id
        schools = School.objects.filter(id=school)
        if len(schools) > 0:
            invite.delete()
            school_user = SchoolUser(school_id=school, user_id=user.id, flags=0, permissions=0)
            school_user.save()
            return APISchool(**dict(schools[0]), owner=schools[0].owner_id == user.id)
    raise HTTPException(status_code=400, detail={
        'message': 'Code is invalid or expired',
        'code': 4035
    })

class CreateSchool(BaseModel):
    name: str
    short_name: str | None

@router.post('/create')
async def create_school(info: CreateSchool, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    if len(info.name) < 1 or len(info.name) > 100:
        raise HTTPException(status_code=400, detail={
            'message': 'School name must be between 1 and 100 characters',
            'code': 9055
        })
    if info.short_name != None:
        if len(info.short_name) < 1 or len(info.name) > 100:
            raise HTTPException(status_code=400, detail={
                'message': 'Short name must be between 1 and 100 characters',
                'code': 9045
            })
    school = School(id=create_snowflake(), name=info.name, short_name=info.short_name, logo_url=None, owner_id=user.id)
    school_user = SchoolUser(school_id=school.id, user_id=user.id, flags=0, permissions=0)
    school.save()
    school_user.save()
    announcements = Channel(school_id=school.id, channel_id=create_snowflake(), name='Announcements', specialty_tag='#front_view, #no_delete', type=0, description='Where all your annoncements live')
    announcements.save()
    return APISchool(**dict(school), owner=True)

@router.get('/{id}/channels/{channel_id}/messages')
async def get_messages(id: int, channel_id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    school_member = get_school_member(user, id)
    channels = Channel.objects.filter(school_id=id, channel_id=channel_id)
    if len(channels) > 0:
        channel = channels[0]
        bucket = make_bucket()
        print(bucket)
        messages = Message.objects.filter(channel_id=channel.channel_id, bucket=bucket).limit(100)
        out_messages: list[Message] = []
        for message in messages:
            out_messages.append(message)
        if len(messages) < 1:
            other_messages = Message.objects.filter(channel_id=channel.channel_id, bucket=bucket-1).limit(100)
            for message in other_messages:
                out_messages.append(message)

        out = []

        for message in out_messages:
            out.append(get_message_data(message))
        
        return out

    raise HTTPException(status_code=400, detail={
        'message': 'Channel or school unavailable',
        'code': 6800
    })

class MessageContent(BaseModel):
    content: str | None

@router.put('/{id}/channels/{channel_id}/messages')
async def create_message(info: MessageContent, id: int, channel_id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    school_member = get_school_member(user, id)
    if not school_member.permissions & SchoolMemberPermissions.MESSAGE_CREATE:
        raise HTTPException(status_code=400, detail={
            'message': 'You do not have permission',
            'code': 90045
        })
    channels = Channel.objects.filter(school_id=id, channel_id=channel_id)
    if len(channels) > 0:
        if info.content != None:
            channel = channels[0]
            id = create_snowflake()
            bucket = make_bucket(id)
            message = Message(channel_id=channel.channel_id, bucket=bucket, message_id=id, author_id=user.id, content=info.content)
            message.save()

            pika_channel.basic_publish(exchange='event', routing_key='message', body=str(get_message_data(message)))
            
            return get_message_data(message)

        raise HTTPException(status_code=400, detail={
            'message': '1 or more fields must be filled',
            'code': 6850
        })

    raise HTTPException(status_code=400, detail={
        'message': 'Channel or school unavailable',
        'code': 6800
    })

@router.delete('/{id}/channels/{channel_id}/messages/{message_id}')
async def delete_message(id: int, channel_id: int, message_id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    school_member = get_school_member(user, id)

    channels = Channel.objects.filter(school_id=id, channel_id=channel_id)
    if len(channels) > 0:
        channel = channels[0]
        messages = Message.objects.filter(channel_id=channel.channel_id, bucket=make_bucket(message_id), message_id=message_id)
        if len(messages):
            message: Message = messages[0]
            if message.author_id == school_member.user_id:
                message.delete()

class ChannelInfo(BaseModel):
    name: str
    description: str | None
    type: int

@router.post('/{id}/channels')
async def create_channel(info: ChannelInfo, id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    school_member = get_school_member(user, id)
    if not info.type >= 0 or not info.type < 3:
        raise HTTPException(status_code=400, detail={
            'message': 'Type is invalid',
            'code': 80000
        })
    if info.name == None:
        raise HTTPException(status_code=400, detail={
            'message': 'Name is not set',
            'code': 80045
        })
    if 1 < len(info.name) > 100:
        raise HTTPException(status_code=400, detail={
            'message': 'Name must be between 1 and 100 characters',
            'code': 80050
        })
    if info.description != None:
        if 1 < len(info.description) > 1000:
            raise HTTPException(status_code=400, detail={
                'message': 'Description must be between 1 and 1000 characters',
                'code': 80055
            })
        
    if school_member.permissions & SchoolMemberPermissions.CHANNEL_CREATE:
        channel = Channel(school_id=id, channel_id=create_snowflake(), description=info.description, name=info.name, type=info.type)
        channel.save()
        return channel.get_pretty()
    else:
        raise HTTPException(status_code=400, detail={
            'message': 'No permission',
            'code': 20000
        })

@router.get('/{id}/channels')
async def get_channels(id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    school_member = get_school_member(user, id)

    channels = Channel.objects.filter(school_id=id)

    out: list[dict] = []
    for channel in channels:
        out.append(channel.get_pretty())

    return out
    
class Invites(BaseModel):
    recipients: list[str]

def generate_code(length: int) -> str:
    return str(randrange(int('1' * length), int('9' * length)))

@router.put('/{id}/invite')
async def invite_users(info: Invites, id: int, authorization: str | None = Header(default=None)):
    user = authorize(authorization)
    school_member = get_school_member(user, id)

    if school_member.permissions & SchoolMemberPermissions.SCHOOL_INVITE:
        code = generate_code(6)
        if not len(info.recipients) > 0:
            raise HTTPException(status_code=400, detail={
                'message': 'No recipients',
                'code': 80000
            })
        for recipient in info.recipients:
            invite = SchoolInvite(email=recipient, code=code, school_id=id, ttl=60*60*24)
            invite.save()
        return {
            'message': 'Invites created',
            'code': 30000
        }

    raise HTTPException(status_code=400, detail={
        'message': 'Failed to create invite. You have no permission',
        'code': 20045
    })