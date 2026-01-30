import { useState } from 'react'
import { Card, Form, Input, Button, Upload, message } from 'antd'
import { SendOutlined, PictureOutlined } from '@ant-design/icons'
import { taskApi } from '../api/client'

const { TextArea } = Input

/**
 * Generation Workbench Component
 * Handles essay topic input (text/image) and task submission
 */
function GenerationWorkbench({ onTaskCreated, onStatusUpdate, onTaskComplete }) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [imageUrl, setImageUrl] = useState(null)

  const handleSubmit = async (values) => {
    if (!values.prompt?.trim() && !imageUrl) {
      message.warning('Please enter a topic or upload an image')
      return
    }

    setLoading(true)
    try {
      const response = await taskApi.create(values.prompt, imageUrl)
      const task = response.data

      onTaskCreated(task)

      // Start SSE stream for progress updates
      const eventSource = taskApi.streamProgress(
        task.task_id,
        (data) => {
          if (data.type === 'progress') {
            onStatusUpdate({
              step: data.agent,
              message: data.message,
            })
          } else if (data.type === 'end') {
            // Fetch final result
            taskApi.getResult(task.task_id).then((res) => {
              onTaskComplete(res.data)
            })
          }
        },
        (error) => {
          message.error('Connection lost. Please refresh.')
        }
      )

      form.resetFields()
      setImageUrl(null)
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to create task')
    } finally {
      setLoading(false)
    }
  }

  const handleImageUpload = (info) => {
    // Placeholder for image upload handling
    // In production, upload to server and get URL
    if (info.file.status === 'done') {
      setImageUrl(info.file.response?.url)
      message.success('Image uploaded')
    }
  }

  return (
    <Card title="Essay Generation Workbench">
      <Form form={form} onFinish={handleSubmit} layout="vertical">
        <Form.Item
          name="prompt"
          label="Essay Topic"
          extra="Enter the Gaokao essay prompt or upload an image"
        >
          <TextArea
            rows={4}
            placeholder="Enter essay topic here..."
            maxLength={2000}
            showCount
          />
        </Form.Item>

        <Form.Item label="Or Upload Topic Image">
          <Upload
            name="image"
            action="/api/upload"
            listType="picture"
            maxCount={1}
            onChange={handleImageUpload}
            accept="image/*"
          >
            <Button icon={<PictureOutlined />}>Upload Image</Button>
          </Upload>
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            icon={<SendOutlined />}
            size="large"
          >
            Generate Essays
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}

export default GenerationWorkbench
