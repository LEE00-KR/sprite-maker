import { useStore } from '../stores/useStore'
import clsx from 'clsx'
import UploadZone from './Upload/UploadZone'
import BackgroundRemoval from './Canvas/BackgroundRemoval'
import PuppetWorkspace from './Canvas/PuppetWorkspace'

function Workspace() {
  const { currentStep, setStep } = useStore()

  const steps = [
    { number: 1, label: '이미지 업로드' },
    { number: 2, label: '배경 삭제' },
    { number: 3, label: '퍼펫 작업' },
  ]

  const renderContent = () => {
    switch (currentStep) {
      case 1:
        return <UploadZone />
      case 2:
        return <BackgroundRemoval />
      case 3:
        return <PuppetWorkspace />
      default:
        return <UploadZone />
    }
  }

  return (
    <section className="workspace">
      {/* 스텝 탭 */}
      <div className="step-tabs">
        {steps.map((step) => (
          <button
            key={step.number}
            className={clsx(
              'step-tab',
              currentStep === step.number && 'active',
              currentStep > step.number && 'completed'
            )}
            onClick={() => setStep(step.number)}
          >
            <span className="step-tab__number">
              {currentStep > step.number ? '✓' : step.number}
            </span>
            <span className="step-tab__label">{step.label}</span>
          </button>
        ))}
      </div>

      {/* 스텝 컨텐츠 */}
      <div className="step-content">
        {renderContent()}
      </div>
    </section>
  )
}

export default Workspace
