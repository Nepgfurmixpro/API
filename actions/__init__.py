from fastapi import APIRouter

from actions.create_user import create_user
from actions.get_user import get_user, get_user_self
from actions.login_user import login_user

router = APIRouter()

#router.add_api_route('/auth/users/create', create_user, methods=['POST'])
#router.add_api_route('/auth/users/login', login_user, methods=['POST'])
#router.add_api_route('/users/@me', get_user_self, methods=['GET'])
#router.add_api_route('/users/{id}', get_user, methods=['GET'])