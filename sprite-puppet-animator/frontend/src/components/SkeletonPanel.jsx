import { useStore } from '../stores/useStore'
import { Trash2 } from 'lucide-react'
import clsx from 'clsx'

function SkeletonPanel() {
  const { 
    character, 
    selection, 
    selectJoint, 
    removeJoint,
    addToast 
  } = useStore()

  // 루트 관절 찾기 (parentId가 null인 것)
  const rootJoints = character.joints.filter((j) => j.parentId === null)
  
  // 자식 관절 찾기
  const getChildren = (parentId) => {
    return character.joints.filter((j) => j.parentId === parentId)
  }

  const handleSelect = (jointId, e) => {
    selectJoint(jointId, e.ctrlKey || e.metaKey)
  }

  const handleDelete = (e, jointId) => {
    e.stopPropagation()
    if (confirm('이 관절과 연결된 뼈대를 삭제하시겠습니까?')) {
      removeJoint(jointId)
      addToast('관절이 삭제되었습니다.', 'info')
    }
  }

  // 재귀적으로 트리 렌더링
  const renderJointTree = (joints, level = 0) => {
    return joints.map((joint) => {
      const children = getChildren(joint.id)
      const isSelected = selection.joints.includes(joint.id)

      return (
        <div key={joint.id} className="tree-node" style={{ paddingLeft: level * 16 }}>
          <div
            className={clsx('tree-node__content', isSelected && 'active')}
            onClick={(e) => handleSelect(joint.id, e)}
          >
            <span 
              className="tree-node__icon"
              style={{ color: joint.color }}
            >
              🔴
            </span>
            <span className="tree-node__label">{joint.name}</span>
            <button
              className="btn btn--icon btn--sm"
              onClick={(e) => handleDelete(e, joint.id)}
              style={{ opacity: 0.5, marginLeft: 'auto' }}
            >
              <Trash2 size={12} />
            </button>
          </div>
          {children.length > 0 && renderJointTree(children, level + 1)}
        </div>
      )
    })
  }

  return (
    <div className="panel">
      <div className="panel__header">
        <h3 className="panel__title">🦴 스켈레톤</h3>
      </div>
      <div className="panel__body">
        {character.joints.length === 0 ? (
          <p className="text-muted" style={{ textAlign: 'center', padding: '20px' }}>
            관절이 없습니다.<br/>
            <small>관절 도구(J)로 추가하세요.</small>
          </p>
        ) : (
          <div className="tree-view">
            {renderJointTree(rootJoints)}
          </div>
        )}
        
        {character.bones.length > 0 && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-color)' }}>
            <small className="text-muted">
              뼈대: {character.bones.length}개
            </small>
          </div>
        )}
      </div>
    </div>
  )
}

export default SkeletonPanel
