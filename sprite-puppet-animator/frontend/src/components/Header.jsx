import { useRef } from 'react'
import { useStore } from '../stores/useStore'
import {
  FileText,
  Save,
  FolderOpen,
  Undo2,
  Redo2,
  Upload,
  Download,
  FileUp
} from 'lucide-react'
import { api } from '../utils/api'

function Header() {
  const fileInputRef = useRef(null)

  const {
    project,
    character,
    newProject,
    openExportModal,
    openCharacterModal,
    getCharacterData,
    exportProjectAsJSON,
    importProjectFromJSON,
    markSaved,
    setLoading,
    addToast,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useStore()

  const handleNew = () => {
    if (!project.saved && character.layers.length > 0) {
      if (!confirm('현재 작업을 저장하지 않고 새 프로젝트를 시작하시겠습니까?')) {
        return
      }
    }
    newProject()
    addToast('새 프로젝트가 생성되었습니다.', 'success')
  }

  // 서버에 저장
  const handleSave = async () => {
    try {
      setLoading(true, '저장 중...')

      const characterData = getCharacterData()

      let result
      if (character.id) {
        // 기존 캐릭터 업데이트
        result = await api.updateCharacter(character.id, characterData)
        addToast('캐릭터가 업데이트되었습니다.', 'success')
      } else {
        // 새 캐릭터 생성
        result = await api.createCharacter(characterData)
        addToast('캐릭터가 저장되었습니다.', 'success')
      }

      markSaved()
    } catch (error) {
      console.error('저장 실패:', error)
      addToast('저장에 실패했습니다. JSON으로 로컬에 저장합니다.', 'warning')
      // 백업으로 JSON 다운로드
      handleDownloadJSON()
    } finally {
      setLoading(false)
    }
  }

  // 서버에서 불러오기
  const handleLoad = () => {
    openCharacterModal()
  }

  // JSON 파일로 다운로드
  const handleDownloadJSON = () => {
    const json = exportProjectAsJSON()
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${project.name || 'project'}.json`
    a.click()
    URL.revokeObjectURL(url)
    addToast('프로젝트가 JSON 파일로 저장되었습니다.', 'success')
  }

  // JSON 파일 가져오기
  const handleImportJSON = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const result = importProjectFromJSON(event.target?.result)
      if (result) {
        addToast('프로젝트를 불러왔습니다.', 'success')
      } else {
        addToast('파일을 읽는데 실패했습니다.', 'error')
      }
    }
    reader.readAsText(file)

    // 입력 초기화 (같은 파일 다시 선택 가능하도록)
    e.target.value = ''
  }

  const handleUndo = () => {
    if (undo) {
      undo()
      addToast('실행 취소', 'info')
    }
  }

  const handleRedo = () => {
    if (redo) {
      redo()
      addToast('다시 실행', 'info')
    }
  }

  return (
    <header className="header">
      {/* 숨겨진 파일 입력 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      <div className="header__logo">
        <span className="header__logo-icon">🎮</span>
        <h1 className="header__logo-title">Sprite Puppet Animator</h1>
        {!project.saved && character.layers.length > 0 && (
          <span style={{ color: 'var(--warning)', marginLeft: 8 }}>●</span>
        )}
      </div>

      <nav className="header__nav">
        <button
          className="btn btn--icon"
          onClick={handleNew}
          title="새 프로젝트"
        >
          <FileText size={18} />
        </button>
        <button
          className="btn btn--icon"
          onClick={handleSave}
          title="서버에 저장"
        >
          <Save size={18} />
        </button>
        <button
          className="btn btn--icon"
          onClick={handleLoad}
          title="서버에서 불러오기"
        >
          <FolderOpen size={18} />
        </button>

        <div className="divider" />

        <button
          className="btn btn--icon"
          onClick={handleDownloadJSON}
          title="JSON으로 내보내기"
        >
          <Download size={18} />
        </button>
        <button
          className="btn btn--icon"
          onClick={handleImportJSON}
          title="JSON 가져오기"
        >
          <FileUp size={18} />
        </button>

        <div className="divider" />

        <button
          className="btn btn--icon"
          onClick={handleUndo}
          title="실행 취소 (Ctrl+Z)"
          disabled={canUndo === false}
          style={{ opacity: canUndo === false ? 0.5 : 1 }}
        >
          <Undo2 size={18} />
        </button>
        <button
          className="btn btn--icon"
          onClick={handleRedo}
          title="다시 실행 (Ctrl+Y)"
          disabled={canRedo === false}
          style={{ opacity: canRedo === false ? 0.5 : 1 }}
        >
          <Redo2 size={18} />
        </button>
      </nav>

      <div className="header__actions">
        <button
          className="btn btn--primary"
          onClick={openExportModal}
        >
          <Upload size={18} />
          내보내기
        </button>
      </div>
    </header>
  )
}

export default Header
