"""
character.py - 캐릭터 모델
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Pydantic과 호환되는 ObjectId"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, schema):
        schema.update(type="string")
        return schema


class Transform(BaseModel):
    """변환 정보"""
    x: float = 0
    y: float = 0
    rotation: float = 0
    scale_x: float = 1
    scale_y: float = 1


class Layer(BaseModel):
    """레이어 모델"""
    id: str
    name: str
    order: int = 0
    image_data: Optional[str] = None  # Base64 이미지 데이터
    visible: bool = True
    opacity: float = 1.0
    transform: Transform = Transform()
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "layer_001",
                "name": "머리",
                "order": 0,
                "visible": True,
                "opacity": 1.0,
            }
        }


class Joint(BaseModel):
    """관절 모델"""
    id: str
    name: str
    x: float
    y: float
    parent_id: Optional[str] = None
    layer_id: Optional[str] = None
    color: str = "#ef4444"
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "joint_001",
                "name": "머리 중심",
                "x": 100,
                "y": 50,
                "parent_id": None,
                "layer_id": "layer_001",
                "color": "#ef4444",
            }
        }


class Bone(BaseModel):
    """뼈대 모델"""
    id: str
    name: str
    start_joint_id: str
    end_joint_id: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "bone_001",
                "name": "목뼈",
                "start_joint_id": "joint_001",
                "end_joint_id": "joint_002",
            }
        }


class SkinningWeights(BaseModel):
    """스키닝 가중치 모델"""
    layer_id: str
    weights: Dict[str, float]  # bone_id -> weight


class Character(BaseModel):
    """캐릭터 모델"""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    thumbnail: Optional[str] = None  # Base64 썸네일
    original_image: Optional[str] = None  # 원본 이미지 Base64
    processed_image: Optional[str] = None  # 배경 제거된 이미지 Base64
    
    layers: List[Layer] = []
    joints: List[Joint] = []
    bones: List[Bone] = []
    skinning_weights: Dict[str, Dict[str, float]] = {}  # layer_id -> {bone_id -> weight}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "기사 캐릭터",
                "layers": [],
                "joints": [],
                "bones": [],
            }
        }
    
    def to_mongo(self) -> dict:
        """MongoDB 저장용 딕셔너리 변환"""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        return data
    
    @classmethod
    def from_mongo(cls, data: dict) -> "Character":
        """MongoDB 문서에서 모델 생성"""
        if data is None:
            return None
        if "_id" in data:
            data["_id"] = str(data["_id"])
        return cls(**data)


class CharacterCreate(BaseModel):
    """캐릭터 생성 요청"""
    name: str
    original_image: Optional[str] = None


class CharacterUpdate(BaseModel):
    """캐릭터 수정 요청"""
    name: Optional[str] = None
    thumbnail: Optional[str] = None
    processed_image: Optional[str] = None
    layers: Optional[List[Layer]] = None
    joints: Optional[List[Joint]] = None
    bones: Optional[Bone] = None
    skinning_weights: Optional[Dict[str, Dict[str, float]]] = None


class CharacterResponse(BaseModel):
    """캐릭터 응답"""
    id: str
    name: str
    thumbnail: Optional[str] = None
    layers_count: int = 0
    joints_count: int = 0
    motions_count: int = 0
    created_at: datetime
    updated_at: datetime
