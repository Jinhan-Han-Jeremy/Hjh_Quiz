from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from app.core.config import settings
from app.core.cache import setup_cache
from app.api.v1 import auth, users
from app.api.deps import get_current_user
from app.db.database import engine, Base, SessionLocal
from app.utils.init_admin import init_admin
from app.api.v1.api import api_router

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 초기 관리자 계정 생성
db = SessionLocal()
try:
    init_admin(db)
finally:
    db.close()

app = FastAPI(
    title="Hjh Quiz API",
    description="퀴즈 관리 API",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router, prefix=settings.API_PREFIX)

# API 라우터 추가
app.include_router(
    auth.router,
    prefix=f"{settings.API_PREFIX}/auth",
    tags=["인증"],
)

app.include_router(
    users.router,
    prefix=f"{settings.API_PREFIX}/users",
    tags=["사용자"],
)

# 페이지네이션 추가
add_pagination(app)

@app.get("/")
def root():
    return {"message": "Welcome to Hjh Quiz API. Go to /api/v1/docs for API documentation."}

# 캐시 설정
@app.on_event("startup")
async def startup_event():
    await setup_cache(app) 