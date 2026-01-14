"""
main.py - FastAPI 애플리케이션 진입점
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.database import Database
from app.api import (
    characters_router,
    motions_router,
    image_router,
    export_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클 관리"""
    # Startup
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 시작...")
    await Database.connect()
    yield
    # Shutdown
    await Database.disconnect()
    print("👋 서버 종료")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="이미지를 업로드하여 배경을 제거하고, 퍼펫 리깅을 통해 애니메이션을 만들어 스프라이트시트/GIF로 내보내는 웹 애플리케이션",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(characters_router, prefix="/api")
app.include_router(motions_router, prefix="/api")
app.include_router(image_router, prefix="/api")
app.include_router(export_router, prefix="/api")


# 헬스 체크
@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# 루트 경로
@app.get("/")
async def root():
    """API 정보"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


# 정적 파일 서빙 (프론트엔드)
# 프로덕션에서 사용
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
