import { useRef, useEffect, useState, useMemo, useCallback } from 'react'
import { useStore } from '../../stores/useStore'
import { ZoomIn, ZoomOut, Maximize, Play, Pause } from 'lucide-react'
import { getAllJointPositionsAtFrame, getLayerTransformFromJoints } from '../../utils/animation'

function PuppetWorkspace() {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const imageCache = useRef({})

  const {
    character,
    currentTool,
    canvas,
    selection,
    timeline,
    currentMotion,
    addJoint,
    addBone,
    updateJoint,
    selectJoint,
    clearSelection,
    setZoom,
    zoomIn,
    zoomOut,
    resetZoom,
    togglePlay,
    addKeyframe,
    addToast,
  } = useStore()

  const [isPanning, setIsPanning] = useState(false)
  const [lastMouse, setLastMouse] = useState({ x: 0, y: 0 })
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })
  const [selectedJointForBone, setSelectedJointForBone] = useState(null)
  const [loadedImages, setLoadedImages] = useState({})

  // 애니메이션된 관절 위치 계산
  const animatedJointPositions = useMemo(() => {
    if (currentMotion.keyframes.length === 0) {
      // 키프레임이 없으면 원본 위치 사용
      return character.joints.reduce((acc, joint) => {
        acc[joint.id] = { x: joint.x, y: joint.y, rotation: 0 }
        return acc
      }, {})
    }
    return getAllJointPositionsAtFrame(
      character.joints,
      timeline.currentFrame,
      currentMotion.keyframes
    )
  }, [character.joints, timeline.currentFrame, currentMotion.keyframes])

  // 이미지 프리로드
  useEffect(() => {
    const newImages = {}
    let loadCount = 0
    const totalImages = character.layers.filter((l) => l.imageData).length

    if (totalImages === 0) return

    character.layers.forEach((layer) => {
      if (layer.imageData && !imageCache.current[layer.id]) {
        const img = new Image()
        img.onload = () => {
          imageCache.current[layer.id] = img
          loadCount++
          if (loadCount === totalImages) {
            setLoadedImages({ ...imageCache.current })
          }
        }
        img.onerror = () => {
          loadCount++
        }
        img.src = layer.imageData
      } else if (imageCache.current[layer.id]) {
        newImages[layer.id] = imageCache.current[layer.id]
      }
    })

    if (Object.keys(newImages).length === totalImages) {
      setLoadedImages(newImages)
    }
  }, [character.layers])

  // 캔버스 그리기
  const draw = useCallback(() => {
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx) return

    const canvasEl = canvasRef.current
    const container = containerRef.current
    if (!container) return

    // 캔버스 크기 설정
    canvasEl.width = container.clientWidth
    canvasEl.height = container.clientHeight

    // 클리어
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height)

    // 배경 격자 그리기
    ctx.save()
    ctx.translate(canvasEl.width / 2 + panOffset.x, canvasEl.height / 2 + panOffset.y)
    ctx.scale(canvas.zoom, canvas.zoom)

    // 레이어 그리기
    character.layers
      .filter((layer) => layer.visible)
      .sort((a, b) => a.order - b.order)
      .forEach((layer) => {
        const img = imageCache.current[layer.id]
        if (img) {
          ctx.save()

          // 애니메이션 적용된 변환 계산
          const transform = getLayerTransformFromJoints(
            layer,
            animatedJointPositions,
            character.joints
          )

          ctx.translate(transform.x, transform.y)
          ctx.rotate((transform.rotation) * Math.PI / 180)
          ctx.scale(transform.scaleX, transform.scaleY)
          ctx.globalAlpha = layer.opacity
          ctx.drawImage(img, -img.width / 2, -img.height / 2)
          ctx.restore()
        }
      })

    // 뼈대 그리기 (애니메이션된 위치 사용)
    character.bones.forEach((bone) => {
      const startPos = animatedJointPositions[bone.startJointId]
      const endPos = animatedJointPositions[bone.endJointId]

      if (startPos && endPos) {
        ctx.beginPath()
        ctx.moveTo(startPos.x, startPos.y)
        ctx.lineTo(endPos.x, endPos.y)
        ctx.strokeStyle = '#94a3b8'
        ctx.lineWidth = 3 / canvas.zoom
        ctx.stroke()
      }
    })

    // 관절 그리기 (애니메이션된 위치 사용)
    character.joints.forEach((joint) => {
      const pos = animatedJointPositions[joint.id]
      if (!pos) return

      const isSelected = selection.joints.includes(joint.id)
      const radius = 8 / canvas.zoom

      ctx.beginPath()
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = isSelected ? '#22d3ee' : joint.color
      ctx.fill()

      if (isSelected) {
        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth = 2 / canvas.zoom
        ctx.stroke()
      }
    })

    ctx.restore()
  }, [character, canvas, panOffset, selection, animatedJointPositions, loadedImages])

  // 캔버스 그리기 실행
  useEffect(() => {
    draw()
  }, [draw])

  // 애니메이션 프레임 업데이트 (재생 중일 때 부드러운 렌더링)
  useEffect(() => {
    if (!timeline.isPlaying) return

    let animationId
    const animate = () => {
      draw()
      animationId = requestAnimationFrame(animate)
    }
    animationId = requestAnimationFrame(animate)

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId)
      }
    }
  }, [timeline.isPlaying, draw])

  // 마우스 좌표를 캔버스 좌표로 변환
  const getCanvasCoords = (e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const canvasEl = canvasRef.current
    
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top
    
    // 캔버스 중심 기준 좌표로 변환
    const x = (mouseX - canvasEl.width / 2 - panOffset.x) / canvas.zoom
    const y = (mouseY - canvasEl.height / 2 - panOffset.y) / canvas.zoom
    
    return { x, y }
  }

  // 관절 찾기 (애니메이션된 위치 기반)
  const findJointAt = (x, y) => {
    const threshold = 15 / canvas.zoom
    return character.joints.find((joint) => {
      const pos = animatedJointPositions[joint.id]
      if (!pos) return false
      const dx = pos.x - x
      const dy = pos.y - y
      return Math.sqrt(dx * dx + dy * dy) < threshold
    })
  }

  // 캔버스 클릭 핸들러
  const handleCanvasClick = (e) => {
    const { x, y } = getCanvasCoords(e)
    const clickedJoint = findJointAt(x, y)

    switch (currentTool) {
      case 'joint':
        // 관절 추가
        addJoint({ x, y })
        addToast('관절이 추가되었습니다.', 'success')
        break

      case 'bone':
        // 뼈대 연결
        if (clickedJoint) {
          if (selectedJointForBone) {
            if (selectedJointForBone !== clickedJoint.id) {
              addBone(selectedJointForBone, clickedJoint.id)
              addToast('뼈대가 연결되었습니다.', 'success')
            }
            setSelectedJointForBone(null)
          } else {
            setSelectedJointForBone(clickedJoint.id)
            selectJoint(clickedJoint.id)
            addToast('두 번째 관절을 선택하세요.', 'info')
          }
        }
        break

      case 'select':
      default:
        if (clickedJoint) {
          selectJoint(clickedJoint.id, e.ctrlKey || e.metaKey)
        } else {
          clearSelection()
        }
        break
    }
  }

  // 마우스 다운
  const handleMouseDown = (e) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      // 중앙 버튼 또는 Alt+클릭으로 패닝
      setIsPanning(true)
      setLastMouse({ x: e.clientX, y: e.clientY })
    }
  }

  // 마우스 이동
  const handleMouseMove = (e) => {
    if (isPanning) {
      const dx = e.clientX - lastMouse.x
      const dy = e.clientY - lastMouse.y
      setPanOffset((prev) => ({ x: prev.x + dx, y: prev.y + dy }))
      setLastMouse({ x: e.clientX, y: e.clientY })
    }

    // 관절 드래그 (선택된 관절)
    if (e.buttons === 1 && selection.joints.length > 0 && currentTool === 'select') {
      const { x, y } = getCanvasCoords(e)
      selection.joints.forEach((jointId) => {
        // 키프레임이 있으면 키프레임 업데이트, 없으면 원본 위치 업데이트
        const hasKeyframes = currentMotion.keyframes.some(
          (kf) => kf.jointId === jointId
        )

        if (hasKeyframes) {
          // 현재 프레임에 키프레임 추가/업데이트
          addKeyframe(jointId, timeline.currentFrame, { x, y })
        } else {
          // 원본 관절 위치 업데이트
          updateJoint(jointId, { x, y })
        }
      })
    }
  }

  // 마우스 업
  const handleMouseUp = () => {
    setIsPanning(false)
  }

  // 휠 줌
  const handleWheel = (e) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    setZoom(canvas.zoom + delta)
  }

  return (
    <div className="canvas-container" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* 서브 탭 */}
      <div className="sub-tabs">
        <button className="sub-tab active">레이어</button>
        <button className="sub-tab">리깅</button>
        <button className="sub-tab">애니메이션</button>
      </div>

      {/* 캔버스 영역 */}
      <div 
        ref={containerRef}
        className="canvas-wrapper"
        style={{ flex: 1, position: 'relative', overflow: 'hidden' }}
      >
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          style={{ 
            display: 'block',
            width: '100%',
            height: '100%',
            cursor: currentTool === 'joint' ? 'crosshair' : 
                   currentTool === 'bone' ? 'pointer' : 
                   isPanning ? 'grabbing' : 'default'
          }}
        />

        {/* 캔버스 컨트롤 */}
        <div className="canvas-controls">
          <button
            className={`btn btn--icon btn--sm ${timeline.isPlaying ? 'active' : ''}`}
            onClick={togglePlay}
            title={timeline.isPlaying ? '일시정지' : '재생'}
            style={{
              background: timeline.isPlaying ? 'var(--primary)' : undefined,
              color: timeline.isPlaying ? 'white' : undefined,
            }}
          >
            {timeline.isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <span style={{ minWidth: 60, textAlign: 'center', fontSize: 11, opacity: 0.8 }}>
            {timeline.currentFrame} / {currentMotion.frameCount - 1}
          </span>
          <div style={{ width: 1, height: 16, background: 'var(--border)' }} />
          <button className="btn btn--icon btn--sm" onClick={zoomOut} title="축소">
            <ZoomOut size={16} />
          </button>
          <span style={{ minWidth: 50, textAlign: 'center', fontSize: 12 }}>
            {Math.round(canvas.zoom * 100)}%
          </span>
          <button className="btn btn--icon btn--sm" onClick={zoomIn} title="확대">
            <ZoomIn size={16} />
          </button>
          <button className="btn btn--icon btn--sm" onClick={resetZoom} title="맞춤">
            <Maximize size={16} />
          </button>
        </div>

        {/* 도구 힌트 */}
        <div 
          style={{
            position: 'absolute',
            top: 16,
            left: 16,
            padding: '8px 12px',
            background: 'var(--bg-panel)',
            borderRadius: 'var(--radius-md)',
            fontSize: 12,
          }}
        >
          {currentTool === 'joint' && '🔴 클릭하여 관절 추가'}
          {currentTool === 'bone' && '🦴 두 관절을 클릭하여 연결'}
          {currentTool === 'select' && '🔲 관절을 클릭하여 선택/드래그'}
        </div>
      </div>
    </div>
  )
}

export default PuppetWorkspace
