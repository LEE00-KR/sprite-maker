"""
config.py - 애플리케이션 설정
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 앱 정보
    APP_NAME: str = "Sprite Puppet Animator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # MongoDB 설정
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "sprite_animator"
    
    # CORS 설정
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]
    
    # 파일 업로드 설정
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".png", ".jpg", ".jpeg", ".webp"]
    UPLOAD_DIR: str = "uploads"
    
    # 이미지 처리 설정
    THUMBNAIL_SIZE: tuple = (128, 128)
    MAX_IMAGE_DIMENSION: int = 2048
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 설정 인스턴스
settings = Settings()

# 업로드 디렉토리 생성
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
