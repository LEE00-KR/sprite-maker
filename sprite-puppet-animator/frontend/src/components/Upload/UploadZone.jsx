import { useState, useRef } from 'react'
import { useStore } from '../../stores/useStore'

const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

function UploadZone() {
  const { setOriginalImage, setProjectName, nextStep, setLoading, addToast } = useStore()
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef(null)

  const handleFile = async (file) => {
    // 유효성 검사
    if (!ALLOWED_TYPES.includes(file.type)) {
      addToast('지원하지 않는 파일 형식입니다.', 'error')
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      addToast('파일 크기가 너무 큽니다. (최대 10MB)', 'error')
      return
    }

    try {
      setLoading(true, '이미지 로딩 중...')

      // Base64로 변환
      const base64 = await fileToBase64(file)
      
      // 상태 업데이트
      setOriginalImage(base64)
      setProjectName(file.name.replace(/\.[^/.]+$/, ''))

      addToast('이미지가 업로드되었습니다.', 'success')
      nextStep() // 다음 단계로

    } catch (error) {
      console.error('파일 업로드 실패:', error)
      addToast('파일 업로드에 실패했습니다.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const fileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  const handleChange = (e) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div
      className={`upload-zone ${isDragOver ? 'dragover' : ''}`}
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="upload-zone__icon">📁</div>
      <div className="upload-zone__text">
        <p>이미지를 드래그하거나 클릭하여 업로드</p>
        <p className="upload-zone__hint">PNG, JPG, JPEG, WEBP (최대 10MB)</p>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleChange}
        style={{ display: 'none' }}
      />
    </div>
  )
}

export default UploadZone
