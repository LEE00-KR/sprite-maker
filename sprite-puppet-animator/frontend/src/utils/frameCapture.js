/**
 * 프레임 캡처 유틸리티
 * 애니메이션 프레임을 이미지로 캡처합니다.
 */

import { getAllJointPositionsAtFrame, getLayerTransformFromJoints } from './animation'

/**
 * 이미지를 로드합니다.
 * @param {string} src - 이미지 소스 (Base64 또는 URL)
 * @returns {Promise<HTMLImageElement>}
 */
export function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

/**
 * 캐릭터의 바운딩 박스를 계산합니다.
 * @param {Object} character - 캐릭터 데이터
 * @param {Object} imageCache - 로드된 이미지 캐시
 * @returns {Object} { x, y, width, height }
 */
export function calculateBoundingBox(character, imageCache) {
  let minX = Infinity, minY = Infinity
  let maxX = -Infinity, maxY = -Infinity

  character.layers.forEach((layer) => {
    if (!layer.visible) return
    const img = imageCache[layer.id]
    if (!img) return

    const transform = layer.transform || { x: 0, y: 0, rotation: 0, scaleX: 1, scaleY: 1 }
    const halfWidth = (img.width / 2) * (transform.scaleX || 1)
    const halfHeight = (img.height / 2) * (transform.scaleY || 1)

    minX = Math.min(minX, (transform.x || 0) - halfWidth)
    minY = Math.min(minY, (transform.y || 0) - halfHeight)
    maxX = Math.max(maxX, (transform.x || 0) + halfWidth)
    maxY = Math.max(maxY, (transform.y || 0) + halfHeight)
  })

  // 관절도 포함
  character.joints.forEach((joint) => {
    minX = Math.min(minX, joint.x - 10)
    minY = Math.min(minY, joint.y - 10)
    maxX = Math.max(maxX, joint.x + 10)
    maxY = Math.max(maxY, joint.y + 10)
  })

  // 유효하지 않은 경우 기본값
  if (!isFinite(minX)) minX = 0
  if (!isFinite(minY)) minY = 0
  if (!isFinite(maxX)) maxX = 256
  if (!isFinite(maxY)) maxY = 256

  const padding = 20
  return {
    x: minX - padding,
    y: minY - padding,
    width: (maxX - minX) + padding * 2,
    height: (maxY - minY) + padding * 2,
  }
}

/**
 * 단일 프레임을 렌더링합니다.
 * @param {Object} character - 캐릭터 데이터
 * @param {Object} motion - 모션 데이터
 * @param {number} frameNumber - 프레임 번호
 * @param {Object} imageCache - 로드된 이미지 캐시
 * @param {Object} options - 옵션 { width, height, backgroundColor }
 * @returns {string} Base64 이미지 데이터
 */
export function renderFrame(character, motion, frameNumber, imageCache, options = {}) {
  const {
    width,
    height,
    backgroundColor,
    boundingBox,
  } = options

  // 애니메이션된 관절 위치 계산
  const jointPositions = getAllJointPositionsAtFrame(
    character.joints,
    frameNumber,
    motion.keyframes
  )

  // 캔버스 생성
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')

  // 바운딩 박스 또는 사용자 지정 크기 사용
  const box = boundingBox || calculateBoundingBox(character, imageCache)
  canvas.width = width || box.width
  canvas.height = height || box.height

  // 배경 색상
  if (backgroundColor) {
    ctx.fillStyle = backgroundColor
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }

  // 변환 설정 (바운딩 박스 중심으로)
  ctx.save()
  ctx.translate(-box.x, -box.y)

  // 레이어 그리기 (순서대로)
  character.layers
    .filter((layer) => layer.visible)
    .sort((a, b) => a.order - b.order)
    .forEach((layer) => {
      const img = imageCache[layer.id]
      if (!img) return

      ctx.save()

      // 애니메이션된 변환 계산
      const transform = getLayerTransformFromJoints(
        layer,
        jointPositions,
        character.joints
      )

      ctx.translate(transform.x, transform.y)
      ctx.rotate((transform.rotation) * Math.PI / 180)
      ctx.scale(transform.scaleX, transform.scaleY)
      ctx.globalAlpha = layer.opacity
      ctx.drawImage(img, -img.width / 2, -img.height / 2)
      ctx.restore()
    })

  ctx.restore()

  // Base64로 변환 (PNG)
  return canvas.toDataURL('image/png').split(',')[1]
}

/**
 * 모든 애니메이션 프레임을 캡처합니다.
 * @param {Object} character - 캐릭터 데이터
 * @param {Object} motion - 모션 데이터
 * @param {Object} options - 옵션 { width, height, backgroundColor, onProgress }
 * @returns {Promise<string[]>} Base64 이미지 배열
 */
export async function captureAllFrames(character, motion, options = {}) {
  const { onProgress } = options

  // 레이어 이미지 프리로드
  const imageCache = {}
  const loadPromises = character.layers
    .filter((layer) => layer.imageData)
    .map(async (layer) => {
      try {
        imageCache[layer.id] = await loadImage(layer.imageData)
      } catch (e) {
        console.warn(`Failed to load layer image: ${layer.id}`)
      }
    })

  await Promise.all(loadPromises)

  // 바운딩 박스 한 번만 계산 (모든 프레임에서 동일한 크기 사용)
  const boundingBox = calculateBoundingBox(character, imageCache)

  // 프레임 렌더링
  const frames = []
  for (let frame = 0; frame < motion.frameCount; frame++) {
    const frameData = renderFrame(character, motion, frame, imageCache, {
      ...options,
      boundingBox,
    })
    frames.push(frameData)

    if (onProgress) {
      onProgress(frame + 1, motion.frameCount)
    }
  }

  return frames
}

/**
 * 프레임 데이터의 크기를 추정합니다.
 * @param {Object} character - 캐릭터 데이터
 * @param {Object} motion - 모션 데이터
 * @returns {Object} { width, height, estimatedSize }
 */
export function estimateExportSize(character, motion) {
  // 대략적인 크기 추정
  const layerCount = character.layers.filter((l) => l.visible && l.imageData).length
  const frameCount = motion.frameCount

  // 가정: 평균 레이어 크기 100KB, 프레임당 압축률 50%
  const estimatedFrameSize = layerCount * 50 // KB
  const totalSize = estimatedFrameSize * frameCount

  return {
    layerCount,
    frameCount,
    estimatedSize: `~${Math.round(totalSize / 1024)}MB`,
  }
}
