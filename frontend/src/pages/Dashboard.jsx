import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, PenTool, RefreshCw } from 'lucide-react';
import TaskInput from '../components/TaskInput';
import ProgressStream from '../components/ProgressStream';
import EssayComparison from '../components/EssayComparison';
import { taskApi, clearToken, isAuthenticated } from '../api/client';

/**
 * Dashboard Page Component
 *
 * Main workbench for essay generation. Integrates:
 * - TaskInput: Form for submitting essay topics
 * - ProgressStream: Real-time SSE progress display
 * - EssayComparison: 3-column essay display with scores
 */
function Dashboard() {
  const navigate = useNavigate();

  // Task state
  const [currentTask, setCurrentTask] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Progress state
  const [currentAgent, setCurrentAgent] = useState(null);
  const [progressMessage, setProgressMessage] = useState('');
  const [progressLogs, setProgressLogs] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isError, setIsError] = useState(false);

  // Results state
  const [essays, setEssays] = useState([]);

  // Auth check on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
    }
  }, [navigate]);

  // Add a log entry
  const addLog = useCallback((agent, message, type = 'info') => {
    setProgressLogs((prev) => [
      ...prev,
      {
        timestamp: Date.now(),
        agent,
        message,
        type,
      },
    ]);
  }, []);

  // Handle task submission
  const handleTaskSubmit = async ({ prompt, imageFile }) => {
    // Reset state
    setCurrentTask(null);
    setCurrentAgent(null);
    setProgressMessage('Submitting task...');
    setProgressLogs([]);
    setIsComplete(false);
    setIsError(false);
    setEssays([]);
    setIsLoading(true);

    try {
      // If there's an image, we'd need to upload it first
      // For now, we'll just use the prompt
      let imageUrl = null;
      if (imageFile) {
        // TODO: Implement image upload endpoint
        addLog('system', 'Image upload not yet implemented, using text prompt only', 'warning');
      }

      // Create the task
      const response = await taskApi.create(prompt, imageUrl);
      const task = response.data;
      setCurrentTask(task);
      addLog('system', `Task created with ID: ${task.id}`);

      // Start SSE stream
      setProgressMessage('Connecting to progress stream...');
      const cleanup = taskApi.streamProgress(task.id, {
        onMessage: (data) => {
          setCurrentAgent(data.agent);
          setProgressMessage(data.message || `${data.agent} is working...`);
          addLog(data.agent, data.message || 'Processing...');
        },
        onComplete: async (data) => {
          setIsComplete(true);
          setProgressMessage('Generation complete!');
          addLog('system', 'All essays generated successfully');

          // Fetch final results
          try {
            const resultResponse = await taskApi.getResult(task.id);
            const result = resultResponse.data;

            // Transform drafts/scores/critiques into essay array
            const essayList = [];
            const styles = ['profound', 'rhetorical', 'steady'];

            for (const style of styles) {
              const draft = result.drafts?.[style];
              if (draft) {
                essayList.push({
                  id: style,
                  style: style,
                  content: draft,
                  score: result.scores?.[style] ?? null,
                  critique: result.critiques?.[style] ?? null,
                  title: style.charAt(0).toUpperCase() + style.slice(1) + ' Essay',
                });
              }
            }

            setEssays(essayList);
            setIsLoading(false);
          } catch (err) {
            addLog('system', 'Failed to fetch final results', 'error');
            setIsLoading(false);
          }
        },
        onError: (error) => {
          setIsError(true);
          setProgressMessage(error.message || 'An error occurred');
          addLog('system', error.message || 'Task failed', 'error');
          setIsLoading(false);
        },
      });

      // Store cleanup function
      return cleanup;
    } catch (err) {
      setIsError(true);
      setProgressMessage(err.response?.data?.detail || 'Failed to create task');
      addLog('system', err.response?.data?.detail || 'Failed to create task', 'error');
      setIsLoading(false);
    }
  };

  // Handle logout
  const handleLogout = () => {
    clearToken();
    navigate('/login');
  };

  // Handle reset
  const handleReset = () => {
    setCurrentTask(null);
    setCurrentAgent(null);
    setProgressMessage('');
    setProgressLogs([]);
    setIsComplete(false);
    setIsError(false);
    setEssays([]);
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl">
                <PenTool className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">BiZhen</h1>
                <p className="text-xs text-gray-500">Gaokao Essay Generation</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-4">
              {(currentTask || essays.length > 0) && (
                <button
                  onClick={handleReset}
                  className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  New Task
                </button>
              )}
              <button
                onClick={handleLogout}
                className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Task Input - Only show when no active task or when complete/error */}
          {(!currentTask || isComplete || isError) && essays.length === 0 && (
            <TaskInput
              onSubmit={handleTaskSubmit}
              isLoading={isLoading}
              disabled={isLoading}
            />
          )}

          {/* Progress Stream - Show when task is active */}
          {currentTask && (
            <ProgressStream
              currentAgent={currentAgent}
              message={progressMessage}
              logs={progressLogs}
              isComplete={isComplete}
              isError={isError}
            />
          )}

          {/* Essay Comparison - Show when complete */}
          {essays.length > 0 && <EssayComparison essays={essays} />}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 text-center text-sm text-gray-400">
        <p>BiZhen Essay Generation System</p>
      </footer>
    </div>
  );
}

export default Dashboard;
