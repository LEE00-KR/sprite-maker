import { useState } from 'react'
import { useStore } from '../../stores/useStore'
import { api } from '../../utils/api'

function BackgroundRemoval() {
  const { 
    character, 
    setProcessedImage, 
    addLayer,
    nextStep, 
    prevStep,
    setLoading, 
    addToast 
  } = useStore()

  const [tolerance, setTolerance] = useState(30)
  const [edgeSmoothing, setEdgeSmoothing] = useState(2)
  const [previewImage, setPreviewImage] = useState(null)

  const handleRemoveBackground = async () => {
    if (!character.originalImage) {
      addToast('먼저 이미지를 업로드해주세요.', 'warning')
      return
    }

    try {
      setLoading(true, '배경 제거 중...')

      const result = await api.removeBackground(
        character.originalImage,
        tolerance,
        edgeSmoothing
      )

      const processedBase64 = `data:image/png;base64,${result.image}`
      setPreviewImage(processedBase64)
      setProcessedImage(processedBase64)

      addToast('배경이 제거되었습니다.', 'success')

    } catch (error) {
      console.error('배경 제거 실패:', error)
      
      // API 실패 시 원본 이미지 사용 (데모용)
      setPreviewImage(character.originalImage)
      setProcessedImage(character.originalImage)
      addToast('배경 제거 API 연결 실패. 원본 이미지를 사용합니다.', 'warning')
    } finally {
      setLoading(false)
    }
  }

  const handleNext = () => {
    const imageToUse = previewImage || character.originalImage
    
    // 기본 레이어로 추가
    addLayer({
      name: '메인',
      imageData: imageToUse,
    })
    
    nextStep()
  }

  const displayImage = previewImage || character.originalImage

  return (
    <div className="canvas-container">
      {/* 이미지 미리보기 */}
      <div className="canvas-wrapper">
        {displayImage ? (
          <div 
            style={{
              position: 'relative',
              maxWidth: '80%',
              maxHeight: '80%',
            }}
          >
            <img
              src={displayImage}
              alt="미리보기"
              style={{
                maxWidth: '100%',
                maxHeight: '500px',
                objectFit: 'contain',
                borderRadius: '8px',
              }}
            />
          </div>
        ) : (
          <p className="text-muted">이미지가 없습니다.</p>
        )}
      </div>

      {/* 컨트롤 패널 */}
      <div 
        style={{
          width: 280,
          padding: 16,
          background: 'var(--bg-sidebar)',
          borderLeft: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>🎨 배경 제거 설정</h3>

        <div className="form-group">
          <label>허용 오차 (Tolerance)</label>
          <input
            type="range"
            min="0"
            max="100"
            value={tolerance}
            onChange={(e) => setTolerance(Number(e.target.value))}
          />
          <span className="text-muted" style={{ fontSize: 12 }}>{tolerance}</span>
        </div>

        <div className="form-group">
          <label>엣지 부드러움</label>
          <input
            type="range"
            min="0"
            max="10"
            value={edgeSmoothing}
            onChange={(e) => setEdgeSmoothing(Number(e.target.value))}
          />
          <span className="text-muted" style={{ fontSize: 12 }}>{edgeSmoothing}</span>
        </div>

        <button 
          className="btn btn--primary btn--block"
          onClick={handleRemoveBackground}
        >
          🎨 배경 제거 실행
        </button>

        <div style={{ marginTop: 'auto', display: 'flex', gap: 8 }}>
          <button className="btn" onClick={prevStep} style={{ flex: 1 }}>
            ← 이전
          </button>
          <button 
            className="btn btn--primary" 
            onClick={handleNext}
            style={{ flex: 1 }}
          >
            다음 →
          </button>
        </div>
      </div>
    </div>
  )
}

export default BackgroundRemoval
