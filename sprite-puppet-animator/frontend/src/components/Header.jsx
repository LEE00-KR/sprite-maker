import { useStore } from '../stores/useStore'
import { 
  FileText, 
  Save, 
  FolderOpen, 
  Undo2, 
  Redo2, 
  Upload 
} from 'lucide-react'

function Header() {
  const { 
    project, 
    newProject, 
    openExportModal,
    openCharacterModal,
    addToast 
  } = useStore()

  const handleNew = () => {
    if (confirm('현재 작업을 저장하지 않고 새 프로젝트를 시작하시겠습니까?')) {
      newProject()
      addToast('새 프로젝트가 생성되었습니다.', 'success')
    }
  }

  const handleSave = () => {
    // TODO: 저장 로직
    addToast('저장되었습니다.', 'success')
  }

  const handleLoad = () => {
    openCharacterModal()
  }

  const handleUndo = () => {
    // TODO: Undo 로직
    addToast('실행 취소', 'info')
  }

  const handleRedo = () => {
    // TODO: Redo 로직
    addToast('다시 실행', 'info')
  }

  return (
    <header className="header">
      <div className="header__logo">
        <span className="header__logo-icon">🎮</span>
        <h1 className="header__logo-title">Sprite Puppet Animator</h1>
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
          title="저장"
        >
          <Save size={18} />
        </button>
        <button 
          className="btn btn--icon" 
          onClick={handleLoad}
          title="불러오기"
        >
          <FolderOpen size={18} />
        </button>
        
        <div className="divider" />
        
        <button 
          className="btn btn--icon" 
          onClick={handleUndo}
          title="실행 취소 (Ctrl+Z)"
        >
          <Undo2 size={18} />
        </button>
        <button 
          className="btn btn--icon" 
          onClick={handleRedo}
          title="다시 실행 (Ctrl+Y)"
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
