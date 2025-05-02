from fastapi import APIRouter

from app.api.v1.endpoints import quiz, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(quiz.router, prefix="/quizzes", tags=["quizzes"]) 