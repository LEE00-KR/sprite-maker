"""
database.py - MongoDB 연결 관리
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from app.config import settings


class Database:
    """MongoDB 데이터베이스 연결 관리"""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """데이터베이스 연결"""
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # 연결 테스트
            try:
                await cls.client.admin.command('ping')
                print(f"✅ MongoDB 연결 성공: {settings.MONGODB_DB_NAME}")
            except Exception as e:
                print(f"❌ MongoDB 연결 실패: {e}")
                raise
    
    @classmethod
    async def disconnect(cls):
        """데이터베이스 연결 해제"""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            print("MongoDB 연결 해제")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """데이터베이스 인스턴스 반환"""
        if cls.db is None:
            raise Exception("Database not connected. Call connect() first.")
        return cls.db
    
    # 컬렉션 접근자
    @classmethod
    def characters(cls):
        """Characters 컬렉션"""
        return cls.get_db().characters
    
    @classmethod
    def motions(cls):
        """Motions 컬렉션"""
        return cls.get_db().motions


# 의존성 주입용
async def get_database() -> AsyncIOMotorDatabase:
    """FastAPI 의존성 주입용 데이터베이스 getter"""
    return Database.get_db()
