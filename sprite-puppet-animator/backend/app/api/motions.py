"""
motions.py - 모션 API 라우터
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
from bson import ObjectId

from app.database import Database
from app.models.motion import (
    Motion,
    MotionCreate,
    MotionUpdate,
    MotionResponse,
    Keyframe,
    KeyframeCreate,
    KeyframeUpdate,
)

router = APIRouter(tags=["Motions"])


# ===== 캐릭터별 모션 엔드포인트 =====

@router.get("/characters/{character_id}/motions", response_model=List[MotionResponse])
async def get_character_motions(character_id: str):
    """
    캐릭터의 모션 목록 조회
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    cursor = Database.motions().find({"character_id": character_id})
    motions = []
    
    async for doc in cursor:
        motion = Motion.from_mongo(doc)
        motions.append(MotionResponse(
            id=str(doc["_id"]),
            character_id=motion.character_id,
            name=motion.name,
            frame_count=motion.frame_count,
            fps=motion.fps,
            loop=motion.loop,
            keyframes_count=len(motion.keyframes),
            created_at=motion.created_at,
            updated_at=motion.updated_at,
        ))
    
    return motions


@router.post("/characters/{character_id}/motions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_motion(character_id: str, data: MotionCreate):
    """
    모션 생성
    """
    if not ObjectId.is_valid(character_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 캐릭터 ID입니다.",
        )
    
    # 캐릭터 존재 확인
    character = await Database.characters().find_one({"_id": ObjectId(character_id)})
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    
    motion = Motion(
        character_id=character_id,
        name=data.name,
        frame_count=data.frame_count,
        fps=data.fps,
        loop=data.loop,
    )
    
    result = await Database.motions().insert_one(motion.to_mongo())
    
    return {
        "id": str(result.inserted_id),
        "message": "모션이 생성되었습니다.",
    }


# ===== 개별 모션 엔드포인트 =====

@router.get("/motions/{motion_id}", response_model=Motion)
async def get_motion(motion_id: str):
    """
    모션 상세 조회
    """
    if not ObjectId.is_valid(motion_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 모션 ID입니다.",
        )
    
    doc = await Database.motions().find_one({"_id": ObjectId(motion_id)})
    
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="모션을 찾을 수 없습니다.",
        )
    
    return Motion.from_mongo(doc)


@router.put("/motions/{motion_id}", response_model=dict)
async def update_motion(motion_id: str, data: MotionUpdate):
    """
    모션 수정
    """
    if not ObjectId.is_valid(motion_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 모션 ID입니다.",
        )
    
    # 업데이트할 필드만 추출
    update_data = data.model_dump(exclude_none=True)
    update_data["updated_at"] = datetime.utcnow()
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 데이터가 없습니다.",
        )
    
    # keyframes가 있으면 Pydantic 모델을 dict로 변환
    if "keyframes" in update_data:
        update_data["keyframes"] = [
            kf.model_dump() if isinstance(kf, Keyframe) else kf 
            for kf in update_data["keyframes"]
        ]
    
    result = await Database.motions().update_one(
        {"_id": ObjectId(motion_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="모션을 찾을 수 없습니다.",
        )
    
    return {"message": "모션이 수정되었습니다."}


@router.delete("/motions/{motion_id}", response_model=dict)
async def delete_motion(motion_id: str):
    """
    모션 삭제
    """
    if not ObjectId.is_valid(motion_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 모션 ID입니다.",
        )
    
    result = await Database.motions().delete_one({"_id": ObjectId(motion_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="모션을 찾을 수 없습니다.",
        )
    
    return {"message": "모션이 삭제되었습니다."}


# ===== 키프레임 엔드포인트 =====

@router.post("/motions/{motion_id}/keyframes", response_model=dict)
async def add_keyframe(motion_id: str, data: KeyframeCreate):
    """
    키프레임 추가
    """
    if not ObjectId.is_valid(motion_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 모션 ID입니다.",
        )
    
    keyframe = Keyframe(
        id=f"kf_{datetime.utcnow().timestamp()}",
        **data.model_dump()
    )
    
    result = await Database.motions().update_one(
        {"_id": ObjectId(motion_id)},
        {
            "$push": {"keyframes": keyframe.model_dump()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="모션을 찾을 수 없습니다.",
        )
    
    return {
        "id": keyframe.id,
        "message": "키프레임이 추가되었습니다.",
    }


@router.put("/motions/{motion_id}/keyframes/{keyframe_id}", response_model=dict)
async def update_keyframe(motion_id: str, keyframe_id: str, data: KeyframeUpdate):
    """
    키프레임 수정
    """
    if not ObjectId.is_valid(motion_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 모션 ID입니다.",
        )
    
    # 업데이트할 필드 생성
    update_fields = {}
    update_data = data.model_dump(exclude_none=True)
    
    for key, value in update_data.items():
        update_fields[f"keyframes.$.{key}"] = value
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 데이터가 없습니다.",
        )
    
    update_fields["updated_at"] = datetime.utcnow()
    
    result = await Database.motions().update_one(
        {
            "_id": ObjectId(motion_id),
            "keyframes.id": keyframe_id
        },
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="모션 또는 키프레임을 찾을 수 없습니다.",
        )
    
    return {"message": "키프레임이 수정되었습니다."}


@router.delete("/motions/{motion_id}/keyframes/{keyframe_id}", response_model=dict)
async def delete_keyframe(motion_id: str, keyframe_id: str):
    """
    키프레임 삭제
    """
    if not ObjectId.is_valid(motion_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 모션 ID입니다.",
        )
    
    result = await Database.motions().update_one(
        {"_id": ObjectId(motion_id)},
        {
            "$pull": {"keyframes": {"id": keyframe_id}},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="모션을 찾을 수 없습니다.",
        )
    
    return {"message": "키프레임이 삭제되었습니다."}


@router.post("/motions/{motion_id}/duplicate", response_model=dict)
async def duplicate_motion(motion_id: str, new_name: str = None):
    """
    모션 복제
    """
    if not ObjectId.is_valid(motion_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 모션 ID입니다.",
        )
    
    # 원본 모션 조회
    doc = await Database.motions().find_one({"_id": ObjectId(motion_id)})
    
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="모션을 찾을 수 없습니다.",
        )
    
    # 복제
    original = Motion.from_mongo(doc)
    duplicated = Motion(
        character_id=original.character_id,
        name=new_name or f"{original.name} (복사본)",
        frame_count=original.frame_count,
        fps=original.fps,
        loop=original.loop,
        keyframes=[
            Keyframe(
                id=f"kf_{datetime.utcnow().timestamp()}_{i}",
                joint_id=kf.joint_id,
                frame_number=kf.frame_number,
                x=kf.x,
                y=kf.y,
                rotation=kf.rotation,
                scale_x=kf.scale_x,
                scale_y=kf.scale_y,
                easing=kf.easing,
            )
            for i, kf in enumerate(original.keyframes)
        ],
    )
    
    result = await Database.motions().insert_one(duplicated.to_mongo())
    
    return {
        "id": str(result.inserted_id),
        "message": "모션이 복제되었습니다.",
    }
