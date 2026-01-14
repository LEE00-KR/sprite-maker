import { useState, useEffect } from 'react'
import { useStore } from '../../stores/useStore'
import { X, Trash2 } from 'lucide-react'
import { api } from '../../utils/api'

function CharacterModal() {
  const { ui, closeCharacterModal, setLoading, addToast } = useStore()
  const [characters, setCharacters] = useState([])

  useEffect(() => {
    if (ui.showCharacterModal) {
      loadCharacters()
    }
  }, [ui.showCharacterModal])

  const loadCharacters = async () => {
    try {
      const data = await api.getCharacters()
      setCharacters(data)
    } catch (error) {
      console.error('캐릭터 목록 로드 실패:', error)
      // 데모용 더미 데이터
      setCharacters([
        { id: '1', name: '기사 캐릭터', thumbnail: null, layers_count: 3, joints_count: 5 },
        { id: '2', name: '마법사', thumbnail: null, layers_count: 4, joints_count: 7 },
      ])
    }
  }

  const handleLoad = async (characterId) => {
    try {
      setLoading(true, '캐릭터 불러오는 중...')
      
      const character = await api.getCharacter(characterId)
      // TODO: 상태에 로드
      
      addToast('캐릭터를 불러왔습니다.', 'success')
      closeCharacterModal()

    } catch (error) {
      console.error('캐릭터 로드 실패:', error)
      addToast('캐릭터를 불러오는데 실패했습니다.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (e, characterId) => {
    e.stopPropagation()
    
    if (!confirm('이 캐릭터를 삭제하시겠습니까?')) return

    try {
      await api.deleteCharacter(characterId)
      setCharacters(characters.filter((c) => c.id !== characterId))
      addToast('캐릭터가 삭제되었습니다.', 'info')
    } catch (error) {
      console.error('캐릭터 삭제 실패:', error)
      addToast('삭제에 실패했습니다.', 'error')
    }
  }

  if (!ui.showCharacterModal) return null

  return (
    <div className="modal-overlay" onClick={closeCharacterModal}>
      <div className="modal modal--wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2>📁 저장된 캐릭터</h2>
          <button className="modal__close" onClick={closeCharacterModal}>
            <X size={20} />
          </button>
        </div>

        <div className="modal__body">
          {characters.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
              저장된 캐릭터가 없습니다.
            </div>
          ) : (
            <div 
              style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
                gap: 16,
              }}
            >
              {characters.map((char) => (
                <div
                  key={char.id}
                  onClick={() => handleLoad(char.id)}
                  style={{
                    padding: 12,
                    background: 'var(--bg-input)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'var(--bg-input)'}
                >
                  {/* 썸네일 */}
                  <div
                    style={{
                      width: '100%',
                      aspectRatio: '1',
                      background: 'var(--bg-panel)',
                      borderRadius: 'var(--radius-sm)',
                      marginBottom: 8,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 48,
                    }}
                  >
                    {char.thumbnail ? (
                      <img 
                        src={char.thumbnail} 
                        alt={char.name}
                        style={{ maxWidth: '100%', maxHeight: '100%' }}
                      />
                    ) : (
                      '🎮'
                    )}
                  </div>

                  {/* 정보 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {char.name}
                    </span>
                    <button
                      className="btn btn--icon btn--sm"
                      onClick={(e) => handleDelete(e, char.id)}
                      style={{ opacity: 0.5 }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                    레이어 {char.layers_count} · 관절 {char.joints_count}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal__footer">
          <button className="btn" onClick={closeCharacterModal}>
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}

export default CharacterModal
