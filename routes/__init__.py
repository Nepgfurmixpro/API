from fastapi import APIRouter
from routes import auth, users, schools

router = APIRouter()

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(schools.router)