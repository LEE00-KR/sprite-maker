import { useState } from 'react'
import { useStore } from '../../stores/useStore'
import { X } from 'lucide-react'
import { api } from '../../utils/api'

function ExportModal() {
  const { ui, closeExportModal, setLoading, addToast } = useStore()
  
  const [exportType, setExportType] = useState('spritesheet')
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

  const handleExport = async () => {
    try {
      setLoading(true, '내보내기 중...')

      // TODO: 실제 프레임 데이터 생성
      const frames = [] // 현재 애니메이션의 프레임들

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
          <button className="btn" onClick={closeExportModal}>
            취소
          </button>
          <button className="btn btn--primary" onClick={handleExport}>
            내보내기
          </button>
        </div>
      </div>
    </div>
  )
}

export default ExportModal
