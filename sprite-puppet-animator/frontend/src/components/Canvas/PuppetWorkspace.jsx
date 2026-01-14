import { useRef, useEffect, useState } from 'react'
import { useStore } from '../../stores/useStore'
import { ZoomIn, ZoomOut, Maximize } from 'lucide-react'

function PuppetWorkspace() {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  
  const { 
    character, 
    currentTool,
    canvas,
    selection,
    addJoint,
    addBone,
    updateJoint,
    selectJoint,
    clearSelection,
    setZoom,
    zoomIn,
    zoomOut,
    resetZoom,
    addToast,
  } = useStore()

  const [isPanning, setIsPanning] = useState(false)
  const [lastMouse, setLastMouse] = useState({ x: 0, y: 0 })
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })
  const [selectedJointForBone, setSelectedJointForBone] = useState(null)

  // 캔버스 그리기
  useEffect(() => {
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx) return

    const canvasEl = canvasRef.current
    const container = containerRef.current
    
    // 캔버스 크기 설정
    canvasEl.width = container.clientWidth
    canvasEl.height = container.clientHeight

    // 클리어
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height)

    // 변환 적용
    ctx.save()
    ctx.translate(canvasEl.width / 2 + panOffset.x, canvasEl.height / 2 + panOffset.y)
    ctx.scale(canvas.zoom, canvas.zoom)

    // 레이어 그리기
    character.layers
      .filter((layer) => layer.visible)
      .sort((a, b) => a.order - b.order)
      .forEach((layer) => {
        if (layer.imageData) {
          const img = new Image()
          img.src = layer.imageData
          
          // 이미지가 로드되면 그리기
          img.onload = () => {
            ctx.save()
            ctx.translate(layer.transform?.x || 0, layer.transform?.y || 0)
            ctx.rotate((layer.transform?.rotation || 0) * Math.PI / 180)
            ctx.scale(layer.transform?.scaleX || 1, layer.transform?.scaleY || 1)
            ctx.globalAlpha = layer.opacity
            ctx.drawImage(img, -img.width / 2, -img.height / 2)
            ctx.restore()
          }
        }
      })

    // 뼈대 그리기
    character.bones.forEach((bone) => {
      const startJoint = character.joints.find((j) => j.id === bone.startJointId)
      const endJoint = character.joints.find((j) => j.id === bone.endJointId)
      
      if (startJoint && endJoint) {
        ctx.beginPath()
        ctx.moveTo(startJoint.x, startJoint.y)
        ctx.lineTo(endJoint.x, endJoint.y)
        ctx.strokeStyle = '#94a3b8'
        ctx.lineWidth = 3 / canvas.zoom
        ctx.stroke()
      }
    })

    // 관절 그리기
    character.joints.forEach((joint) => {
      const isSelected = selection.joints.includes(joint.id)
      const radius = 8 / canvas.zoom
      
      ctx.beginPath()
      ctx.arc(joint.x, joint.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = isSelected ? '#22d3ee' : joint.color
      ctx.fill()
      
      if (isSelected) {
        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth = 2 / canvas.zoom
        ctx.stroke()
      }
    })

    ctx.restore()
  }, [character, canvas, panOffset, selection])

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

  // 관절 찾기
  const findJointAt = (x, y) => {
    const threshold = 15 / canvas.zoom
    return character.joints.find((joint) => {
      const dx = joint.x - x
      const dy = joint.y - y
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
        updateJoint(jointId, { x, y })
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
