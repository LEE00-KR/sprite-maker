"""
motion.py - 모션(애니메이션) 모델
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from bson import ObjectId


class Keyframe(BaseModel):
    """키프레임 모델"""
    id: str
    joint_id: str
    frame_number: int
    x: float
    y: float
    rotation: float = 0
    scale_x: float = 1
    scale_y: float = 1
    easing: Literal["linear", "ease-in", "ease-out", "ease-in-out", "step"] = "linear"
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "kf_001",
                "joint_id": "joint_001",
                "frame_number": 0,
                "x": 100,
                "y": 50,
                "rotation": 0,
                "easing": "ease-in-out",
            }
        }


class Motion(BaseModel):
    """모션 모델"""
    id: Optional[str] = Field(default=None, alias="_id")
    character_id: str
    name: str
    frame_count: int = 30
    fps: int = 12
    loop: bool = True
    
    keyframes: List[Keyframe] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "character_id": "64abc123def456",
                "name": "걷기",
                "frame_count": 30,
                "fps": 12,
                "loop": True,
                "keyframes": [],
            }
        }
    
    def to_mongo(self) -> dict:
        """MongoDB 저장용 딕셔너리 변환"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "Motion":
        """MongoDB 문서에서 모델 생성"""
        if data is None:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])
        return cls(**data)


class MotionCreate(BaseModel):
    """모션 생성 요청"""
    name: str
    frame_count: int = 30
    fps: int = 12
    loop: bool = True


class MotionUpdate(BaseModel):
    """모션 수정 요청"""
    name: Optional[str] = None
    frame_count: Optional[int] = None
    fps: Optional[int] = None
    loop: Optional[bool] = None
    keyframes: Optional[List[Keyframe]] = None


class MotionResponse(BaseModel):
    """모션 응답"""
    id: str
    character_id: str
    name: str
    frame_count: int
    fps: int
    loop: bool
    keyframes_count: int = 0
    created_at: datetime
    updated_at: datetime


class KeyframeCreate(BaseModel):
    """키프레임 생성 요청"""
    joint_id: str
    frame_number: int
    x: float
    y: float
    rotation: float = 0
    scale_x: float = 1
    scale_y: float = 1
    easing: Literal["linear", "ease-in", "ease-out", "ease-in-out", "step"] = "linear"


class KeyframeUpdate(BaseModel):
    """키프레임 수정 요청"""
    x: Optional[float] = None
    y: Optional[float] = None
    rotation: Optional[float] = None
    scale_x: Optional[float] = None
    scale_y: Optional[float] = None
    easing: Optional[Literal["linear", "ease-in", "ease-out", "ease-in-out", "step"]] = None
