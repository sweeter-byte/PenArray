import { Steps, Card } from 'antd'
import {
  BulbOutlined,
  SearchOutlined,
  OrderedListOutlined,
  EditOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'

/**
 * Agent step configuration
 */
const AGENT_STEPS = [
  { key: 'strategist', title: 'Strategist', icon: <BulbOutlined />, description: 'Analyzing topic...' },
  { key: 'librarian', title: 'Librarian', icon: <SearchOutlined />, description: 'Retrieving materials...' },
  { key: 'outliner', title: 'Outliner', icon: <OrderedListOutlined />, description: 'Creating outline...' },
  { key: 'writer', title: 'Writers', icon: <EditOutlined />, description: 'Writing essays...' },
  { key: 'grader', title: 'Grader', icon: <CheckCircleOutlined />, description: 'Scoring essays...' },
  { key: 'completed', title: 'Complete', icon: <CheckCircleOutlined />, description: 'Done!' },
]

/**
 * Get current step index based on agent status
 */
function getCurrentStep(agentKey) {
  const index = AGENT_STEPS.findIndex((step) => step.key === agentKey)
  return index >= 0 ? index : 0
}

/**
 * Progress Stepper Component
 * Displays current agent status in the workflow
 */
function ProgressStepper({ status }) {
  const currentStep = getCurrentStep(status?.step)

  const items = AGENT_STEPS.map((step, index) => ({
    key: step.key,
    title: step.title,
    description: index === currentStep ? status?.message : step.description,
    icon: index === currentStep && status?.step !== 'completed'
      ? <LoadingOutlined />
      : step.icon,
    status: index < currentStep
      ? 'finish'
      : index === currentStep
        ? 'process'
        : 'wait',
  }))

  return (
    <Card className="progress-container">
      <Steps
        current={currentStep}
        items={items}
        size="small"
      />
    </Card>
  )
}

export default ProgressStepper
