import { useStore } from '../../stores/useStore'
import clsx from 'clsx'

// 도구 정의
const tools = [
  {
    section: '선택',
    items: [
      { id: 'select', icon: '🔲', label: '선택 도구', shortcut: 'V' },
      { id: 'move', icon: '✋', label: '이동 도구', shortcut: 'M' },
    ],
  },
  {
    section: '그리기',
    items: [
      { id: 'pen', icon: '✏️', label: '펜 도구', shortcut: 'P' },
      { id: 'rect', icon: '⬜', label: '사각형 선택', shortcut: 'R' },
      { id: 'ellipse', icon: '⭕', label: '원형 선택', shortcut: 'E' },
      { id: 'polygon', icon: '🔷', label: '다각형 선택', shortcut: 'L' },
    ],
  },
  {
    section: '리깅',
    items: [
      { id: 'joint', icon: '🔴', label: '관절 추가', shortcut: 'J' },
      { id: 'bone', icon: '🦴', label: '뼈대 연결', shortcut: 'B' },
      { id: 'pin', icon: '📌', label: '고정점', shortcut: 'N' },
    ],
  },
  {
    section: '편집',
    items: [
      { id: 'cut', icon: '✂️', label: '오려내기', shortcut: 'Ctrl+X' },
      { id: 'fill', icon: '🎨', label: '채우기', shortcut: 'F' },
      { id: 'transform', icon: '🔄', label: '변형', shortcut: 'T' },
      { id: 'eraser', icon: '🧹', label: '지우개', shortcut: 'X' },
    ],
  },
]

function Toolbar() {
  const { currentTool, setTool } = useStore()

  return (
    <div className="toolbar">
      {tools.map((section) => (
        <div key={section.section} className="toolbar__section">
          <span className="toolbar__label">{section.section}</span>
          {section.items.map((tool) => (
            <button
              key={tool.id}
              className={clsx('tool-btn', currentTool === tool.id && 'active')}
              onClick={() => setTool(tool.id)}
              title={`${tool.label} (${tool.shortcut})`}
            >
              <span>{tool.icon}</span>
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}

export default Toolbar
