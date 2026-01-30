import { Form, Input, Button } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'

/**
 * Reusable Login Form Component
 */
function LoginForm({ onSubmit, loading }) {
  return (
    <Form
      name="loginForm"
      onFinish={onSubmit}
      autoComplete="off"
      layout="vertical"
    >
      <Form.Item
        name="username"
        rules={[{ required: true, message: 'Please enter username' }]}
      >
        <Input
          prefix={<UserOutlined />}
          placeholder="Username"
          size="large"
        />
      </Form.Item>

      <Form.Item
        name="password"
        rules={[{ required: true, message: 'Please enter password' }]}
      >
        <Input.Password
          prefix={<LockOutlined />}
          placeholder="Password"
          size="large"
        />
      </Form.Item>

      <Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          block
          size="large"
        >
          Login
        </Button>
      </Form.Item>
    </Form>
  )
}

export default LoginForm
