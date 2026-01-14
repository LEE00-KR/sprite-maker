"""
characters.py - 캐릭터 API 라우터
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
from bson import ObjectId

from app.database import Database
from app.models.character import (
    Character, 
    CharacterCreate, 
    CharacterUpdate, 
    CharacterResponse
)

router = APIRouter(prefix="/characters", tags=["Characters"])


@router.get("", response_model=List[CharacterResponse])
async def get_characters():
    """
    캐릭터 목록 조회
    """
    cursor = Database.characters().find()
    characters = []
    
    async for doc in cursor:
        character = Character.from_mongo(doc)
        
        # 모션 수 조회
        motions_count = await Database.motions().count_documents(
            {"character_id": str(doc["_id"])}
        )
        
        characters.append(CharacterResponse(
            id=str(doc["_id"]),
            name=character.name,
            thumbnail=character.thumbnail,
            layers_count=len(character.layers),
            joints_count=len(character.joints),
            motions_count=motions_count,
            created_at=character.created_at,
            updated_at=character.updated_at,
        ))
    
    return characters


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_character(data: CharacterCreate):
    """
    캐릭터 생성
    """
    character = Character(
        name=data.name,
        original_image=data.original_image,
    )
    
    result = await Database.characters().insert_one(character.to_mongo())
    
    return {
        "id": str(result.inserted_id),
        "message": "캐릭터가 생성되었습니다.",
    }


@router.get("/{character_id}", response_model=Character)
async def get_character(character_id: str):
    """
    캐릭터 상세 조회
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    doc = await Database.characters().find_one({"_id": ObjectId(character_id)})
    
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return Character.from_mongo(doc)


@router.put("/{character_id}", response_model=dict)
async def update_character(character_id: str, data: CharacterUpdate):
    """
    캐릭터 수정
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    # 업데이트할 필드만 추출
    update_data = data.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.utcnow()
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 데이터가 없습니다.",
        )
    
    result = await Database.characters().update_one(
        {"_id": ObjectId(character_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return {"message": "캐릭터가 수정되었습니다."}


@router.delete("/{character_id}", response_model=dict)
async def delete_character(character_id: str):
    """
    캐릭터 삭제 (관련 모션도 함께 삭제)
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    # 캐릭터 삭제
    result = await Database.characters().delete_one({"_id": ObjectId(character_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    # 관련 모션 삭제
    await Database.motions().delete_many({"character_id": character_id})
    
    return {"message": "캐릭터와 관련 모션이 삭제되었습니다."}


# ===== 레이어 관련 엔드포인트 =====

@router.post("/{character_id}/layers", response_model=dict)
async def add_layer(character_id: str, layer: dict):
    """
    레이어 추가
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    result = await Database.characters().update_one(
        {"_id": ObjectId(character_id)},
        {
            "$push": {"layers": layer},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return {"message": "레이어가 추가되었습니다."}


@router.delete("/{character_id}/layers/{layer_id}", response_model=dict)
async def remove_layer(character_id: str, layer_id: str):
    """
    레이어 삭제
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    result = await Database.characters().update_one(
        {"_id": ObjectId(character_id)},
        {
            "$pull": {"layers": {"id": layer_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return {"message": "레이어가 삭제되었습니다."}


# ===== 관절 관련 엔드포인트 =====

@router.post("/{character_id}/joints", response_model=dict)
async def add_joint(character_id: str, joint: dict):
    """
    관절 추가
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    result = await Database.characters().update_one(
        {"_id": ObjectId(character_id)},
        {
            "$push": {"joints": joint},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return {"message": "관절이 추가되었습니다."}


@router.delete("/{character_id}/joints/{joint_id}", response_model=dict)
async def remove_joint(character_id: str, joint_id: str):
    """
    관절 삭제 (연결된 뼈대도 함께 삭제)
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    # 관절 삭제 및 연결된 뼈대 삭제
    result = await Database.characters().update_one(
        {"_id": ObjectId(character_id)},
        {
            "$pull": {
                "joints": {"id": joint_id},
                "bones": {
                    "$or": [
                        {"start_joint_id": joint_id},
                        {"end_joint_id": joint_id}
                    ]
                }
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return {"message": "관절이 삭제되었습니다."}


# ===== 뼈대 관련 엔드포인트 =====

@router.post("/{character_id}/bones", response_model=dict)
async def add_bone(character_id: str, bone: dict):
    """
    뼈대 추가
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    result = await Database.characters().update_one(
        {"_id": ObjectId(character_id)},
        {
            "$push": {"bones": bone},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return {"message": "뼈대가 추가되었습니다."}


@router.delete("/{character_id}/bones/{bone_id}", response_model=dict)
async def remove_bone(character_id: str, bone_id: str):
    """
    뼈대 삭제
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    result = await Database.characters().update_one(
        {"_id": ObjectId(character_id)},
        {
            "$pull": {"bones": {"id": bone_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    return {"message": "뼈대가 삭제되었습니다."}
