import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout, Button, Typography } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import GenerationWorkbench from '../components/GenerationWorkbench'
import ProgressStepper from '../components/ProgressStepper'
import EssayDisplay from '../components/EssayDisplay'

const { Header, Content } = Layout
const { Title } = Typography

/**
 * Dashboard Page Component
 * Main workspace for essay generation
 */
function Dashboard() {
  const navigate = useNavigate()
  const [currentTask, setCurrentTask] = useState(null)
  const [agentStatus, setAgentStatus] = useState(null)
  const [essays, setEssays] = useState([])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/login')
    }
  }, [navigate])

  const handleLogout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  const handleTaskCreated = (task) => {
    setCurrentTask(task)
    setEssays([])
    setAgentStatus({ step: 'queued', message: 'Task queued...' })
  }

  const handleStatusUpdate = (status) => {
    setAgentStatus(status)
  }

  const handleTaskComplete = (result) => {
    setEssays(result.essays || [])
    setAgentStatus({ step: 'completed', message: 'Generation complete!' })
  }

  return (
    <Layout className="dashboard-container">
      <Header style={{ background: '#fff', padding: '0 24px' }}>
        <div className="dashboard-header">
          <Title level={3} style={{ margin: 0 }}>BiZhen Dashboard</Title>
          <Button
            icon={<LogoutOutlined />}
            onClick={handleLogout}
          >
            Logout
          </Button>
        </div>
      </Header>
      <Content style={{ padding: '24px' }}>
        <GenerationWorkbench
          onTaskCreated={handleTaskCreated}
          onStatusUpdate={handleStatusUpdate}
          onTaskComplete={handleTaskComplete}
        />

        {agentStatus && (
          <ProgressStepper status={agentStatus} />
        )}

        {essays.length > 0 && (
          <EssayDisplay essays={essays} />
        )}
      </Content>
    </Layout>
  )
}

export default Dashboard
