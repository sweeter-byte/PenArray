import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, PenTool, RefreshCw, AlertTriangle, X } from 'lucide-react';
import TaskInput from '../components/TaskInput';
import ProgressStream from '../components/ProgressStream';
import EssayComparison from '../components/EssayComparison';
import { taskApi, clearToken, isAuthenticated } from '../api/client';

// localStorage keys for session persistence
const STORAGE_KEYS = {
  ESSAYS: 'bizhen_essays',
  CURRENT_TASK: 'bizhen_current_task',
  INPUT_PROMPT: 'bizhen_input_prompt',
  INTERMEDIATE_DATA: 'bizhen_intermediate_data',
};

/**
 * Logout Confirmation Modal Component
 */
function LogoutModal({ isOpen, onConfirm, onCancel }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 text-amber-600 mb-4">
          <AlertTriangle className="w-8 h-8" />
          <h3 className="text-lg font-bold">确认退出登录</h3>
        </div>

        <p className="text-gray-600 mb-6">
          退出登录将会<span className="text-red-600 font-medium">清除所有已生成的作文内容</span>。
          请确保您已保存需要的文档后再退出。
        </p>

        <div className="flex space-x-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
          >
            确认退出
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Dashboard Page Component
 *
 * Main workbench for essay generation. Integrates:
 * - TaskInput: Form for submitting essay topics
 * - ProgressStream: Real-time SSE progress display
 * - EssayComparison: 3-column essay display with scores
 * - Session persistence via localStorage
 */
function Dashboard() {
  const navigate = useNavigate();

  // Task state
  const [currentTask, setCurrentTask] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [inputPrompt, setInputPrompt] = useState('');

  // Progress state
  const [currentAgent, setCurrentAgent] = useState(null);
  const [progressMessage, setProgressMessage] = useState('');
  const [progressLogs, setProgressLogs] = useState([]);
  const [isComplete, setIsComplete] = useState(false);
  const [isError, setIsError] = useState(false);

  // Results state
  const [essays, setEssays] = useState([]);

  // Intermediate data for process transparency
  const [intermediateData, setIntermediateData] = useState({});

  // Logout modal state
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  // Auth check on mount
  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
    }
  }, [navigate]);

  // Restore session from localStorage on mount
  useEffect(() => {
    try {
      const savedEssays = localStorage.getItem(STORAGE_KEYS.ESSAYS);
      const savedTask = localStorage.getItem(STORAGE_KEYS.CURRENT_TASK);
      const savedPrompt = localStorage.getItem(STORAGE_KEYS.INPUT_PROMPT);
      const savedIntermediate = localStorage.getItem(STORAGE_KEYS.INTERMEDIATE_DATA);

      if (savedEssays) {
        const parsedEssays = JSON.parse(savedEssays);
        if (Array.isArray(parsedEssays) && parsedEssays.length > 0) {
          setEssays(parsedEssays);
          setIsComplete(true);
        }
      }

      if (savedTask) {
        setCurrentTask(JSON.parse(savedTask));
      }

      if (savedPrompt) {
        setInputPrompt(savedPrompt);
      }

      if (savedIntermediate) {
        setIntermediateData(JSON.parse(savedIntermediate));
      }
    } catch (err) {
      console.error('Failed to restore session:', err);
    }
  }, []);

  // Save essays to localStorage when they change
  useEffect(() => {
    if (essays.length > 0) {
      localStorage.setItem(STORAGE_KEYS.ESSAYS, JSON.stringify(essays));
    }
  }, [essays]);

  // AUTO-RESUME LOGIC: Check status of pending task on load
  useEffect(() => {
    let cleanupStream = null;

    const resumeTask = async () => {
      // Only resume if we have a task, NO essays yet, and we aren't already loading/complete
      if (currentTask && essays.length === 0 && !isComplete && !isLoading) {
        console.log('Resuming pending task:', currentTask.task_id);
        setIsLoading(true);

        try {
          // 1. Check current status from backend
          const statusRes = await taskApi.getStatus(currentTask.task_id);
          const status = statusRes.data.status;
          console.log('Task status on resume:', status);

          if (status === 'completed') {
            // 2a. If already done, fetch result immediately
            setProgressMessage('检测到任务已完成，正在获取结果...');
            const resultResponse = await taskApi.getResult(currentTask.task_id);
            const result = resultResponse.data;

            // Reuse result processing logic
            console.log('Resume - Final Result:', result);

            // Backfill intermediate data for modals
            const backfillData = {};

            // 1. Strategist/Librarian/Outliner from meta_info
            if (result.meta_info) {
              backfillData.strategist = {
                message: '审题分析完成',
                data: {
                  angle: result.meta_info.angle,
                  thesis: result.meta_info.thesis,
                  style_params: result.meta_info.style_params // Ensure this is passed if available
                }
              };
              backfillData.librarian = {
                message: '素材检索完成',
                data: result.meta_info.materials
              };
              backfillData.outliner = {
                message: '大纲生成完成',
                data: result.meta_info.outline
              };
            }

            // 2. Writer/Grader from essays/drafts
            const essaysToProcess = (result.essays && result.essays.length > 0) ? result.essays : [];
            // If legacy drafts format...
            if (essaysToProcess.length === 0 && result.drafts) {
              ['profound', 'rhetorical', 'steady'].forEach(style => {
                if (result.drafts[style]) {
                  essaysToProcess.push({
                    style,
                    content: result.drafts[style],
                    score: result.scores?.[style],
                    critique: result.critiques?.[style]
                  });
                }
              });
            }

            if (essaysToProcess.length > 0) {
              // Mock Writer Data
              backfillData.writer = {
                message: '写作完成',
                data: essaysToProcess.map(e => `【${e.style === 'profound' ? '深刻型' : e.style === 'rhetorical' ? '文采型' : '稳健型'}】\n${e.content.substring(0, 100)}...`).join('\n\n')
              };
              // Mock Grader Data
              backfillData.grader = {
                message: '评分完成',
                data: essaysToProcess.map(e => `【${e.style}】得分：${e.score}\n评语：${e.critique ? e.critique.substring(0, 50) + '...' : '暂无'}`).join('\n')
              };

              // Set Reviser/Reviewer as 'completed' generic
              backfillData.reviser = { message: '修订完成', data: '文章已根据评分意见进行修订。' };
              backfillData.reviewer = { message: '审核通过', data: '所有文章已通过最终质量审核。' };
            }

            setIntermediateData(backfillData);

            if (result.essays && Array.isArray(result.essays) && result.essays.length > 0) {
              setEssays(result.essays);
            } else if (result.drafts) {
              // Fallback logic
              const essayList = [];
              const styles = ['profound', 'rhetorical', 'steady'];
              for (const style of styles) {
                if (draft) {
                  essayList.push({
                    id: style,
                    style: style,
                    content: draft,
                    score: result.scores?.[style] ?? null,
                    critique: result.critiques?.[style] ?? null,
                    title: (result.titles?.[style]) || (style.charAt(0).toUpperCase() + style.slice(1) + ' Essay'),
                  });
                }
              }
              setEssays(essayList);
            }
            setIsComplete(true);
            setIsLoading(false);

          } else if (status === 'failed') {
            setIsError(true);
            setProgressMessage('任务此前已失败');
            setIsLoading(false);
          } else {
            // 2b. If still processing/queued, reconnect stream
            setProgressMessage('正在恢复进度连接...');
            cleanupStream = taskApi.streamProgress(currentTask.task_id, {
              onMessage: (data) => {
                setCurrentAgent(data.agent);
                setProgressMessage(data.message || `${data.agent} 正在工作...`);
                addLog(data.agent, data.message || '处理中... (已恢复连接)');

                if (data.data) {
                  setIntermediateData((prev) => ({
                    ...prev,
                    [data.agent]: {
                      message: data.message,
                      data: data.data,
                      timestamp: Date.now(),
                    },
                  }));
                }
              },
              onComplete: async () => {
                // When stream says complete, fetch result
                setIsComplete(true);
                setProgressMessage('生成完成！');
                try {
                  const rRes = await taskApi.getResult(currentTask.task_id);
                  const res = rRes.data;
                  if (res.essays && Array.isArray(res.essays) && res.essays.length > 0) {
                    setEssays(res.essays);
                  } else if (res.drafts) {
                    // fallback logic copy
                    const essayList = [];
                    const styles = ['profound', 'rhetorical', 'steady'];
                    for (const style of styles) {
                      const draft = res.drafts[style];
                      if (draft) {
                        essayList.push({
                          id: style, style: style, content: draft,
                          score: res.scores?.[style] ?? null,
                          critique: res.critiques?.[style] ?? null,
                          title: (res.titles?.[style]) || (style.charAt(0).toUpperCase() + style.slice(1) + ' Essay'),
                        });
                      }
                    }
                    setEssays(essayList);
                  }
                  setIsLoading(false);
                } catch (e) { console.error(e); setIsLoading(false); }
              },
              onError: (err) => {
                console.error('Stream error on resume', err);
                // Don't fail immediately on stream error, maybe just polling?
                // For now, simple error
                addLog('system', '连接断开', 'error');
              }
            });
          }
        } catch (err) {
          console.error('Failed to resume task:', err);
          setIsError(true);
          setProgressMessage('无法恢复任务进度');
          setIsLoading(false);
        }
      }
    };

    resumeTask();

    return () => {
      if (cleanupStream) cleanupStream();
    };
  }, [currentTask]); // Depend on currentTask (which is set on mount)

  // Save current task to localStorage
  useEffect(() => {
    if (currentTask) {
      localStorage.setItem(STORAGE_KEYS.CURRENT_TASK, JSON.stringify(currentTask));
    }
  }, [currentTask]);

  // Save intermediate data to localStorage
  useEffect(() => {
    if (Object.keys(intermediateData).length > 0) {
      localStorage.setItem(STORAGE_KEYS.INTERMEDIATE_DATA, JSON.stringify(intermediateData));
    }
  }, [intermediateData]);

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
  const handleTaskSubmit = async ({ prompt, imageFile, customStructure }) => {
    // Reset state
    setCurrentTask(null);
    setCurrentAgent(null);
    setProgressMessage('正在提交任务...');
    setProgressLogs([]);
    setIsComplete(false);
    setIsError(false);
    setEssays([]);
    setIntermediateData({});
    setIsLoading(true);

    try {
      let finalPrompt = prompt;
      let imageUrl = null;

      // Check if image upload is needed
      if (imageFile) {
        setProgressMessage('正在识别图片内容...');
        addLog('system', '正在上传并识别图片...');

        try {
          // Upload image
          const uploadRes = await taskApi.upload(imageFile);
          const { url, text } = uploadRes.data;

          imageUrl = url;
          addLog('system', '图片上传成功');

          if (text) {
            addLog('system', `OCR识别成功: ${text.substring(0, 20)}...`);
            // Should we replace prompt if empty?
            if (!finalPrompt.trim()) {
              finalPrompt = text;
              // Update UI prompt state too so it reflects
              setInputPrompt(text);
              localStorage.setItem(STORAGE_KEYS.INPUT_PROMPT, text);
            } else {
              // User provided prompt + image.
              // We append the OCR text to prompt for context, or just keep it separately?
              // Strategy: Pass image_url to backend, but also if prompt was small, maybe user expects OCR.
              // For now, let's append if prompt is short, or just rely on backend?
              // The backend `create_task` takes `prompt` and `image_url`.
              // If prompt is empty, we MUST fill it.
              // If prompt is not empty, we leave it as is.
            }
          } else {
            addLog('system', '未识别到文字，将仅作为参考图片上传', 'warning');
          }

        } catch (uploadErr) {
          console.error("Upload failed", uploadErr);
          addLog('system', '图片上传失败，尝试继续仅使用文字...', 'error');
          // If prompt is empty and upload failed, we must stop
          if (!finalPrompt.trim()) {
            throw new Error('图片上传失败且未输入题目文字');
          }
        }
      }

      if (!finalPrompt.trim()) {
        throw new Error('请输入题目或上传包含文字的图片');
      }

      // Create the task with optional custom structure
      const response = await taskApi.create(finalPrompt, imageUrl, customStructure);
      const task = response.data;
      setCurrentTask(task);
      addLog('system', `任务已创建，ID: ${task.task_id}`);

      // Start SSE stream
      setProgressMessage('正在连接进度流...');
      const cleanup = taskApi.streamProgress(task.task_id, {
        onMessage: (data) => {
          setCurrentAgent(data.agent);
          setProgressMessage(data.message || `${data.agent} 正在工作...`);
          addLog(data.agent, data.message || '处理中...');

          // Collect intermediate data for process transparency
          if (data.data) {
            setIntermediateData((prev) => ({
              ...prev,
              [data.agent]: {
                message: data.message,
                data: data.data,
                timestamp: Date.now(),
              },
            }));
          }
        },
        onComplete: async (data) => {
          setIsComplete(true);
          setProgressMessage('生成完成！');
          addLog('system', '所有作文生成成功');

          // Fetch final results
          try {
            const resultResponse = await taskApi.getResult(task.task_id);
            const result = resultResponse.data;

            // Store intermediate data from task meta_info
            if (result.meta_info) {
              setIntermediateData((prev) => ({
                ...prev,
                strategist: {
                  message: '审题分析完成',
                  data: {
                    angle: result.meta_info.angle,
                    thesis: result.meta_info.thesis,
                  },
                },
                librarian: {
                  message: '素材检索完成',
                  data: result.meta_info.materials,
                },
                outliner: {
                  message: '大纲生成完成',
                  data: result.meta_info.outline,
                },
              }));
            }

            console.log('Final Result Received:', result); // DEBUG Log

            // Transform API response essays array
            if (result.essays && Array.isArray(result.essays) && result.essays.length > 0) {
              console.log('Setting essays from result.essays:', result.essays);
              setEssays(result.essays);
            } else if (result.drafts) {
              // Fallback for legacy format or meta_info populated format
              console.log('Setting essays from result.drafts fallback');
              const essayList = [];
              const styles = ['profound', 'rhetorical', 'steady'];

              for (const style of styles) {
                const draft = result.drafts[style]; // Access directly as object
                if (draft) {
                  essayList.push({
                    id: style, // Use style as ID for draft mode
                    style: style,
                    content: draft,
                    score: result.scores?.[style] ?? null,
                    critique: result.critiques?.[style] ?? null,
                    title: (result.titles?.[style]) || (style.charAt(0).toUpperCase() + style.slice(1) + ' Essay'),
                  });
                }
              }
              setEssays(essayList);
            } else {
              console.error('No essays found in result:', result);
            }
            setIsLoading(false);
          } catch (err) {
            addLog('system', '获取最终结果失败', 'error');
            setIsLoading(false);
          }
        },
        onError: (error) => {
          setIsError(true);
          setProgressMessage(error.message || '发生错误');
          addLog('system', error.message || '任务失败', 'error');
          setIsLoading(false);
        },
      });

      // Store cleanup function
      return cleanup;
    } catch (err) {
      setIsError(true);
      setProgressMessage(err.response?.data?.detail || '创建任务失败');
      addLog('system', err.response?.data?.detail || '创建任务失败', 'error');
      setIsLoading(false);
    }
  };

  // Handle logout with confirmation
  const handleLogoutClick = () => {
    setShowLogoutModal(true);
  };

  const handleLogoutConfirm = () => {
    // Clear all session data
    Object.values(STORAGE_KEYS).forEach((key) => {
      localStorage.removeItem(key);
    });
    clearToken();
    navigate('/login');
  };

  const handleLogoutCancel = () => {
    setShowLogoutModal(false);
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
    setIntermediateData({});
    setIsLoading(false);
    setInputPrompt('');

    // Clear localStorage
    Object.values(STORAGE_KEYS).forEach((key) => {
      localStorage.removeItem(key);
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Logout Confirmation Modal */}
      <LogoutModal
        isOpen={showLogoutModal}
        onConfirm={handleLogoutConfirm}
        onCancel={handleLogoutCancel}
      />

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
                <h1 className="text-xl font-bold text-gray-900">笔阵</h1>
                <p className="text-xs text-gray-500">高考作文智能生成系统</p>
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
                  新任务
                </button>
              )}
              <button
                onClick={handleLogoutClick}
                className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4 mr-2" />
                退出登录
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
              initialPrompt={inputPrompt}
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
              intermediateData={intermediateData}
            />
          )}

          {/* Essay Comparison - Show when complete */}
          {essays.length > 0 && <EssayComparison essays={essays} />}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 text-center text-sm text-gray-400">
        <p>笔阵 - 高考作文智能生成系统</p>
      </footer>
    </div>
  );
}

export default Dashboard;
