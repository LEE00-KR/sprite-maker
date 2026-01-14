import { useState } from 'react'
import { useStore } from '../../stores/useStore'
import { X, Loader } from 'lucide-react'
import { api } from '../../utils/api'
import { captureAllFrames, estimateExportSize } from '../../utils/frameCapture'

function ExportModal() {
  const { ui, character, currentMotion, closeExportModal, setLoading, addToast } = useStore()

  const [exportType, setExportType] = useState('spritesheet')
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [isCapturing, setIsCapturing] = useState(false)
  const [settings, setSettings] = useState({
    // 스프라이트시트
    columns: 5,
    padding: 0,

    // GIF
    fps: 12,
    loop: true,

    // 공통
    width: null,
    height: null,
    backgroundColor: '',
  })

  if (!ui.showExportModal) return null

  // 내보내기 예상 정보
  const exportInfo = estimateExportSize(character, currentMotion)

  const handleExport = async () => {
    // 레이어가 없으면 내보내기 불가
    if (character.layers.filter((l) => l.visible && l.imageData).length === 0) {
      addToast('내보낼 레이어가 없습니다.', 'warning')
      return
    }

    try {
      setIsCapturing(true)
      setProgress({ current: 0, total: currentMotion.frameCount })

      // 프레임 캡처
      const frames = await captureAllFrames(character, currentMotion, {
        width: settings.width || null,
        height: settings.height || null,
        backgroundColor: settings.backgroundColor || null,
        onProgress: (current, total) => {
          setProgress({ current, total })
        },
      })

      setIsCapturing(false)
      setLoading(true, '서버에서 처리 중...')

      let result
      switch (exportType) {
        case 'spritesheet':
          result = await api.exportSpritesheet({
            frames,
            columns: settings.columns,
            padding: settings.padding,
            backgroundColor: settings.backgroundColor || null,
          })
          downloadBase64('spritesheet.png', result.image, 'image/png')
          break

        case 'gif':
          result = await api.exportGif({
            frames,
            fps: settings.fps,
            loop: settings.loop ? 0 : 1,
            backgroundColor: settings.backgroundColor || null,
          })
          downloadBase64('animation.gif', result.gif, 'image/gif')
          break

        case 'png-sequence':
          result = await api.exportPngSequence({
            frames,
            prefix: 'frame',
          })
          downloadBase64('frames.zip', result.zip, 'application/zip')
          break
      }

      addToast('내보내기가 완료되었습니다.', 'success')
      closeExportModal()

    } catch (error) {
      console.error('내보내기 실패:', error)
      addToast('내보내기에 실패했습니다.', 'error')
    } finally {
      setIsCapturing(false)
      setLoading(false)
    }
  }

  const downloadBase64 = (filename, base64, mimeType) => {
    const link = document.createElement('a')
    link.href = `data:${mimeType};base64,${base64}`
    link.download = filename
    link.click()
  }

  return (
    <div className="modal-overlay" onClick={closeExportModal}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2>📤 내보내기</h2>
          <button className="modal__close" onClick={closeExportModal}>
            <X size={20} />
          </button>
        </div>

        <div className="modal__body">
          {/* 프레임 캡처 진행률 */}
          {isCapturing && (
            <div
              style={{
                padding: 16,
                background: 'var(--bg-active)',
                borderRadius: 'var(--radius-md)',
                marginBottom: 16,
                textAlign: 'center',
              }}
            >
              <Loader
                size={24}
                style={{ animation: 'spin 1s linear infinite', marginBottom: 8 }}
              />
              <div>프레임 캡처 중...</div>
              <div style={{ fontSize: 14, opacity: 0.8 }}>
                {progress.current} / {progress.total}
              </div>
              <div
                style={{
                  height: 4,
                  background: 'var(--border)',
                  borderRadius: 2,
                  marginTop: 8,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${(progress.current / progress.total) * 100}%`,
                    background: 'var(--primary)',
                    transition: 'width 0.2s',
                  }}
                />
              </div>
            </div>
          )}

          {/* 내보내기 정보 */}
          <div
            style={{
              padding: 12,
              background: 'var(--bg-active)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 16,
              fontSize: 13,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>레이어 수:</span>
              <strong>{exportInfo.layerCount}개</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>프레임 수:</span>
              <strong>{exportInfo.frameCount}프레임</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>예상 크기:</span>
              <strong>{exportInfo.estimatedSize}</strong>
            </div>
          </div>

          {/* 내보내기 타입 선택 */}
          <div className="form-group">
            <label>내보내기 형식</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {[
                { id: 'spritesheet', label: '스프라이트시트', icon: '🎞️' },
                { id: 'gif', label: 'GIF 애니메이션', icon: '🎬' },
                { id: 'png-sequence', label: 'PNG 시퀀스', icon: '📁' },
              ].map((type) => (
                <button
                  key={type.id}
                  className={`btn ${exportType === type.id ? 'btn--primary' : ''}`}
                  onClick={() => setExportType(type.id)}
                  style={{ flex: 1 }}
                >
                  {type.icon} {type.label}
                </button>
              ))}
            </div>
          </div>

          {/* 스프라이트시트 설정 */}
          {exportType === 'spritesheet' && (
            <>
              <div className="form-group">
                <label>열 개수</label>
                <input
                  type="number"
                  value={settings.columns}
                  onChange={(e) => setSettings({ ...settings, columns: Number(e.target.value) })}
                  min={1}
                  max={20}
                />
              </div>
              <div className="form-group">
                <label>프레임 간격 (px)</label>
                <input
                  type="number"
                  value={settings.padding}
                  onChange={(e) => setSettings({ ...settings, padding: Number(e.target.value) })}
                  min={0}
                  max={50}
                />
              </div>
            </>
          )}

          {/* GIF 설정 */}
          {exportType === 'gif' && (
            <>
              <div className="form-group">
                <label>FPS</label>
                <select
                  value={settings.fps}
                  onChange={(e) => setSettings({ ...settings, fps: Number(e.target.value) })}
                >
                  <option value={6}>6</option>
                  <option value={8}>8</option>
                  <option value={12}>12</option>
                  <option value={24}>24</option>
                  <option value={30}>30</option>
                </select>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={settings.loop}
                    onChange={(e) => setSettings({ ...settings, loop: e.target.checked })}
                    style={{ width: 'auto', marginRight: 8 }}
                  />
                  반복 재생
                </label>
              </div>
            </>
          )}

          {/* 공통 설정 */}
          <div className="form-group">
            <label>배경색 (비워두면 투명)</label>
            <input
              type="color"
              value={settings.backgroundColor || '#ffffff'}
              onChange={(e) => setSettings({ ...settings, backgroundColor: e.target.value })}
              style={{ width: 60, height: 32, padding: 0 }}
            />
            <button
              className="btn btn--sm"
              onClick={() => setSettings({ ...settings, backgroundColor: '' })}
              style={{ marginLeft: 8 }}
            >
              투명
            </button>
          </div>
        </div>

        <div className="modal__footer">
          <button className="btn" onClick={closeExportModal} disabled={isCapturing}>
            취소
          </button>
          <button
            className="btn btn--primary"
            onClick={handleExport}
            disabled={isCapturing || exportInfo.layerCount === 0}
          >
            {isCapturing ? '캡처 중...' : '내보내기'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ExportModal
