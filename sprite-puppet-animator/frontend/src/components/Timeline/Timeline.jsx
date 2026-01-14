import { useEffect, useRef, useState } from 'react'
import { useStore } from '../../stores/useStore'
import { 
  Play, 
  Pause, 
  SkipBack, 
  SkipForward, 
  Plus,
  Repeat,
  Trash2
} from 'lucide-react'

function Timeline() {
  const {
    character,
    currentMotion,
    timeline,
    selection,
    setCurrentFrame,
    setPlaying,
    togglePlay,
    toggleLoop,
    setFps,
    setFrameCount,
    addKeyframe,
    removeKeyframe,
    addToast,
  } = useStore()

  const playIntervalRef = useRef(null)
  const FRAME_WIDTH = 30

  // 재생 로직
  useEffect(() => {
    if (timeline.isPlaying) {
      playIntervalRef.current = setInterval(() => {
        setCurrentFrame(
          timeline.currentFrame >= currentMotion.frameCount - 1
            ? timeline.isLooping ? 0 : currentMotion.frameCount - 1
            : timeline.currentFrame + 1
        )
      }, 1000 / currentMotion.fps)
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current)
      }
    }

    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current)
      }
    }
  }, [timeline.isPlaying, timeline.isLooping, currentMotion.fps, currentMotion.frameCount])

  // 처음으로
  const handleGoToStart = () => {
    setCurrentFrame(0)
  }

  // 끝으로
  const handleGoToEnd = () => {
    setCurrentFrame(currentMotion.frameCount - 1)
  }

  // 키프레임 추가
  const handleAddKeyframe = () => {
    if (selection.joints.length === 0) {
      addToast('먼저 관절을 선택해주세요.', 'warning')
      return
    }

    selection.joints.forEach((jointId) => {
      const joint = character.joints.find((j) => j.id === jointId)
      if (joint) {
        addKeyframe(jointId, timeline.currentFrame, {
          x: joint.x,
          y: joint.y,
        })
      }
    })

    addToast('키프레임이 추가되었습니다.', 'success')
  }

  // 프레임 클릭
  const handleFrameClick = (frameNumber) => {
    setCurrentFrame(frameNumber)
  }

  // 키프레임 클릭
  const handleKeyframeClick = (e, keyframe) => {
    e.stopPropagation()
    // 키프레임 선택 로직
  }

  // 룰러 생성
  const renderRuler = () => {
    const marks = []
    for (let i = 0; i < currentMotion.frameCount; i++) {
      marks.push(
        <div 
          key={i} 
          className="timeline__ruler-mark"
          onClick={() => handleFrameClick(i)}
        >
          {i % 5 === 0 ? i : ''}
        </div>
      )
    }
    return marks
  }

  // 관절별 트랙 그룹화
  const jointKeyframes = character.joints.map((joint) => ({
    joint,
    keyframes: currentMotion.keyframes.filter((kf) => kf.jointId === joint.id),
  }))

  return (
    <div className="timeline-container">
      <div className="timeline">
        {/* 타임라인 헤더 */}
        <div className="timeline__header">
          <div className="timeline__controls">
            <button 
              className="btn btn--icon btn--sm" 
              onClick={handleGoToStart}
              title="처음으로"
            >
              <SkipBack size={16} />
            </button>
            <button 
              className="btn btn--icon btn--sm" 
              onClick={togglePlay}
              title={timeline.isPlaying ? '일시정지' : '재생'}
            >
              {timeline.isPlaying ? <Pause size={16} /> : <Play size={16} />}
            </button>
            <button 
              className="btn btn--icon btn--sm" 
              onClick={handleGoToEnd}
              title="끝으로"
            >
              <SkipForward size={16} />
            </button>
            <button 
              className={`btn btn--icon btn--sm ${timeline.isLooping ? 'active' : ''}`}
              onClick={toggleLoop}
              title="반복"
              style={{ 
                background: timeline.isLooping ? 'var(--bg-active)' : 'transparent' 
              }}
            >
              <Repeat size={16} />
            </button>
          </div>

          <div className="timeline__info">
            <span>
              <strong>{timeline.currentFrame}</strong> / {currentMotion.frameCount - 1}
            </span>
            <label>
              FPS:
              <select 
                value={currentMotion.fps} 
                onChange={(e) => setFps(Number(e.target.value))}
              >
                <option value={6}>6</option>
                <option value={8}>8</option>
                <option value={12}>12</option>
                <option value={24}>24</option>
                <option value={30}>30</option>
                <option value={60}>60</option>
              </select>
            </label>
            <label>
              프레임:
              <select 
                value={currentMotion.frameCount} 
                onChange={(e) => setFrameCount(Number(e.target.value))}
              >
                <option value={15}>15</option>
                <option value={30}>30</option>
                <option value={60}>60</option>
                <option value={90}>90</option>
                <option value={120}>120</option>
              </select>
            </label>
          </div>

          <div className="timeline__actions">
            <button 
              className="btn btn--sm" 
              onClick={handleAddKeyframe}
              title="키프레임 추가"
            >
              <Plus size={14} />
              키프레임
            </button>
          </div>
        </div>

        {/* 타임라인 본문 */}
        <div className="timeline__body">
          {/* 룰러 */}
          <div className="timeline__ruler">
            <div style={{ width: 100, background: 'var(--bg-panel)' }} />
            {renderRuler()}
          </div>

          {/* 트랙 */}
          <div className="timeline__tracks">
            {jointKeyframes.length === 0 ? (
              <div 
                style={{ 
                  padding: 32, 
                  textAlign: 'center', 
                  color: 'var(--text-muted)' 
                }}
              >
                관절을 추가하면 트랙이 표시됩니다.
              </div>
            ) : (
              jointKeyframes.map(({ joint, keyframes }) => (
                <div key={joint.id} className="timeline__track">
                  <div className="timeline__track-label">
                    <span style={{ color: joint.color }}>●</span> {joint.name}
                  </div>
                  <div className="timeline__track-frames">
                    {/* 프레임 셀 */}
                    {Array.from({ length: currentMotion.frameCount }).map((_, i) => (
                      <div 
                        key={i} 
                        className="timeline__frame-cell"
                        onClick={() => handleFrameClick(i)}
                      />
                    ))}
                    
                    {/* 키프레임 */}
                    {keyframes.map((kf) => (
                      <div
                        key={kf.id}
                        className="timeline__keyframe"
                        style={{ left: kf.frameNumber * FRAME_WIDTH + FRAME_WIDTH / 2 }}
                        onClick={(e) => handleKeyframeClick(e, kf)}
                        title={`프레임 ${kf.frameNumber}`}
                      />
                    ))}
                  </div>
                </div>
              ))
            )}

            {/* 플레이헤드 */}
            <div 
              className="timeline__playhead"
              style={{ 
                left: 100 + timeline.currentFrame * FRAME_WIDTH + FRAME_WIDTH / 2,
                height: Math.max(100, jointKeyframes.length * 28 + 24)
              }}
            >
              <div className="playhead__marker" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Timeline
