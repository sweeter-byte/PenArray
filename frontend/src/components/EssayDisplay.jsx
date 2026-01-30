import { Card, Typography, Tag, Rate, Tooltip } from 'antd'

const { Title, Paragraph, Text } = Typography

/**
 * Style configuration for essay cards
 */
const STYLE_CONFIG = {
  profound: {
    title: 'Profound (Deep)',
    titleCn: 'Profound (Deep)',
    color: '#722ed1',
    description: 'Philosophical depth and logical rigor',
  },
  rhetorical: {
    title: 'Rhetorical (Literary)',
    titleCn: 'Rhetorical (Literary)',
    color: '#13c2c2',
    description: 'Elegant prose and rhetorical flourish',
  },
  steady: {
    title: 'Steady (Reliable)',
    titleCn: 'Steady (Reliable)',
    color: '#52c41a',
    description: 'Structured and consistent approach',
  },
}

/**
 * Single Essay Card Component
 */
function EssayCard({ essay }) {
  const config = STYLE_CONFIG[essay.style] || STYLE_CONFIG.steady
  const scorePercent = essay.score ? (essay.score / 60) * 5 : 0

  return (
    <Card
      className={`essay-card ${essay.style}`}
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            <Tag color={config.color}>{config.title}</Tag>
            {essay.title && <Text strong>{essay.title}</Text>}
          </span>
          {essay.score && (
            <Tooltip title={`Score: ${essay.score}/60`}>
              <Rate disabled value={scorePercent} allowHalf />
            </Tooltip>
          )}
        </div>
      }
    >
      <Paragraph className="essay-content">
        {essay.content}
      </Paragraph>

      {essay.critique && (
        <Card
          size="small"
          type="inner"
          title="Grader Comments"
          style={{ marginTop: 16 }}
        >
          <Text type="secondary">{essay.critique}</Text>
        </Card>
      )}
    </Card>
  )
}

/**
 * Essay Display Component
 * Shows three essays side-by-side in a 3-column layout
 */
function EssayDisplay({ essays }) {
  // Sort essays by style order: profound, rhetorical, steady
  const sortedEssays = [...essays].sort((a, b) => {
    const order = ['profound', 'rhetorical', 'steady']
    return order.indexOf(a.style) - order.indexOf(b.style)
  })

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>Generated Essays</Title>
      <div className="essay-grid">
        {sortedEssays.map((essay, index) => (
          <EssayCard key={essay.id || index} essay={essay} />
        ))}
      </div>
    </div>
  )
}

export default EssayDisplay
