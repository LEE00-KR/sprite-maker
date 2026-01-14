/**
 * 애니메이션 보간 유틸리티
 * 키프레임 사이의 중간값을 계산합니다.
 */

// 이징 함수들
export const easingFunctions = {
  // 선형 보간
  linear: (t) => t,

  // Ease In (가속)
  easeIn: (t) => t * t,
  easeInCubic: (t) => t * t * t,
  easeInQuart: (t) => t * t * t * t,

  // Ease Out (감속)
  easeOut: (t) => 1 - (1 - t) * (1 - t),
  easeOutCubic: (t) => 1 - Math.pow(1 - t, 3),
  easeOutQuart: (t) => 1 - Math.pow(1 - t, 4),

  // Ease In-Out (가속 후 감속)
  easeInOut: (t) => t < 0.5
    ? 2 * t * t
    : 1 - Math.pow(-2 * t + 2, 2) / 2,
  easeInOutCubic: (t) => t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2,

  // 탄성
  easeOutElastic: (t) => {
    const c4 = (2 * Math.PI) / 3
    return t === 0 ? 0 : t === 1 ? 1
      : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1
  },

  // 바운스
  easeOutBounce: (t) => {
    const n1 = 7.5625
    const d1 = 2.75
    if (t < 1 / d1) {
      return n1 * t * t
    } else if (t < 2 / d1) {
      return n1 * (t -= 1.5 / d1) * t + 0.75
    } else if (t < 2.5 / d1) {
      return n1 * (t -= 2.25 / d1) * t + 0.9375
    } else {
      return n1 * (t -= 2.625 / d1) * t + 0.984375
    }
  },
}

/**
 * 두 값 사이를 보간합니다.
 * @param {number} start - 시작 값
 * @param {number} end - 끝 값
 * @param {number} t - 진행도 (0~1)
 * @param {string} easing - 이징 함수 이름
 * @returns {number} 보간된 값
 */
export function lerp(start, end, t, easing = 'linear') {
  const easingFn = easingFunctions[easing] || easingFunctions.linear
  const easedT = easingFn(Math.max(0, Math.min(1, t)))
  return start + (end - start) * easedT
}

/**
 * 특정 관절의 현재 프레임 위치를 계산합니다.
 * @param {string} jointId - 관절 ID
 * @param {number} currentFrame - 현재 프레임
 * @param {Array} keyframes - 전체 키프레임 배열
 * @param {Object} originalJoint - 원본 관절 데이터
 * @returns {Object} { x, y, rotation } 계산된 위치
 */
export function getJointPositionAtFrame(jointId, currentFrame, keyframes, originalJoint) {
  // 해당 관절의 키프레임만 필터링
  const jointKeyframes = keyframes
    .filter((kf) => kf.jointId === jointId)
    .sort((a, b) => a.frameNumber - b.frameNumber)

  // 키프레임이 없으면 원본 위치 반환
  if (jointKeyframes.length === 0) {
    return {
      x: originalJoint.x,
      y: originalJoint.y,
      rotation: 0,
    }
  }

  // 첫 키프레임 이전이면 첫 키프레임 값 반환
  if (currentFrame <= jointKeyframes[0].frameNumber) {
    return {
      x: jointKeyframes[0].x,
      y: jointKeyframes[0].y,
      rotation: jointKeyframes[0].rotation || 0,
    }
  }

  // 마지막 키프레임 이후면 마지막 키프레임 값 반환
  const lastKeyframe = jointKeyframes[jointKeyframes.length - 1]
  if (currentFrame >= lastKeyframe.frameNumber) {
    return {
      x: lastKeyframe.x,
      y: lastKeyframe.y,
      rotation: lastKeyframe.rotation || 0,
    }
  }

  // 현재 프레임이 속한 구간 찾기
  let prevKeyframe = jointKeyframes[0]
  let nextKeyframe = jointKeyframes[1]

  for (let i = 0; i < jointKeyframes.length - 1; i++) {
    if (currentFrame >= jointKeyframes[i].frameNumber &&
        currentFrame < jointKeyframes[i + 1].frameNumber) {
      prevKeyframe = jointKeyframes[i]
      nextKeyframe = jointKeyframes[i + 1]
      break
    }
  }

  // 보간 계산
  const frameDiff = nextKeyframe.frameNumber - prevKeyframe.frameNumber
  const progress = frameDiff > 0
    ? (currentFrame - prevKeyframe.frameNumber) / frameDiff
    : 0

  const easing = nextKeyframe.easing || 'linear'

  return {
    x: lerp(prevKeyframe.x, nextKeyframe.x, progress, easing),
    y: lerp(prevKeyframe.y, nextKeyframe.y, progress, easing),
    rotation: lerp(
      prevKeyframe.rotation || 0,
      nextKeyframe.rotation || 0,
      progress,
      easing
    ),
  }
}

/**
 * 모든 관절의 현재 프레임 위치를 계산합니다.
 * @param {Array} joints - 관절 배열
 * @param {number} currentFrame - 현재 프레임
 * @param {Array} keyframes - 전체 키프레임 배열
 * @returns {Object} { jointId: { x, y, rotation } } 관절별 위치 맵
 */
export function getAllJointPositionsAtFrame(joints, currentFrame, keyframes) {
  const positions = {}

  joints.forEach((joint) => {
    positions[joint.id] = getJointPositionAtFrame(
      joint.id,
      currentFrame,
      keyframes,
      joint
    )
  })

  return positions
}

/**
 * 레이어에 연결된 관절 기반으로 레이어 변환을 계산합니다.
 * @param {Object} layer - 레이어 객체
 * @param {Object} jointPositions - 관절별 위치 맵
 * @param {Array} joints - 관절 배열
 * @returns {Object} { x, y, rotation, scaleX, scaleY } 변환값
 */
export function getLayerTransformFromJoints(layer, jointPositions, joints) {
  // 레이어에 연결된 관절 찾기
  const linkedJoint = joints.find((j) => j.layerId === layer.id)

  if (!linkedJoint || !jointPositions[linkedJoint.id]) {
    return {
      x: layer.transform?.x || 0,
      y: layer.transform?.y || 0,
      rotation: layer.transform?.rotation || 0,
      scaleX: layer.transform?.scaleX || 1,
      scaleY: layer.transform?.scaleY || 1,
    }
  }

  const pos = jointPositions[linkedJoint.id]
  const originalJoint = joints.find((j) => j.id === linkedJoint.id)

  // 원본 위치와의 차이를 레이어에 적용
  const deltaX = pos.x - originalJoint.x
  const deltaY = pos.y - originalJoint.y

  return {
    x: (layer.transform?.x || 0) + deltaX,
    y: (layer.transform?.y || 0) + deltaY,
    rotation: (layer.transform?.rotation || 0) + (pos.rotation || 0),
    scaleX: layer.transform?.scaleX || 1,
    scaleY: layer.transform?.scaleY || 1,
  }
}

/**
 * 애니메이션 프레임 데이터를 생성합니다 (내보내기용).
 * @param {Object} character - 캐릭터 데이터
 * @param {Object} motion - 모션 데이터
 * @returns {Array} 프레임별 관절 위치 배열
 */
export function generateAnimationFrames(character, motion) {
  const frames = []

  for (let frame = 0; frame < motion.frameCount; frame++) {
    const jointPositions = getAllJointPositionsAtFrame(
      character.joints,
      frame,
      motion.keyframes
    )

    frames.push({
      frame,
      joints: jointPositions,
      layers: character.layers.map((layer) => ({
        id: layer.id,
        transform: getLayerTransformFromJoints(layer, jointPositions, character.joints),
      })),
    })
  }

  return frames
}
