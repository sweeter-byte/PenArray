import { useState, useEffect, useRef } from 'react';
import {
  Lightbulb,
  Search,
  ListOrdered,
  PenTool,
  CheckCircle,
  Loader2,
  AlertCircle,
  BookOpen,
  Star,
  X,
  Eye,
  FileEdit,
  ShieldCheck,
} from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';

/**
 * Agent step configuration
 */
const AGENT_STEPS = [
  {
    key: 'strategist',
    name: '策划师',
    nameCn: '策划师',
    icon: Lightbulb,
    description: '正在分析题目，确定立意角度...',
    color: 'text-amber-500',
    bgColor: 'bg-amber-100',
    modalTitle: '审题分析结果',
  },
  {
    key: 'librarian',
    name: '资料员',
    nameCn: '资料员',
    icon: Search,
    description: '正在检索素材和论据...',
    color: 'text-blue-500',
    bgColor: 'bg-blue-100',
    modalTitle: '素材检索结果',
  },
  {
    key: 'outliner',
    name: '大纲师',
    nameCn: '大纲师',
    icon: ListOrdered,
    description: '正在生成文章大纲...',
    color: 'text-green-500',
    bgColor: 'bg-green-100',
    modalTitle: '文章大纲',
  },
  {
    key: 'writer',
    name: '写手组',
    nameCn: '写手组',
    icon: PenTool,
    description: '三位写手正在创作不同风格的作文...',
    color: 'text-purple-500',
    bgColor: 'bg-purple-100',
    subSteps: ['writer_profound', 'writer_rhetorical', 'writer_steady'],
    modalTitle: '写作进度',
  },
  {
    key: 'grader',
    name: '评分组',
    nameCn: '评分组',
    icon: Star,
    description: '正在评阅和打分...',
    color: 'text-orange-500',
    bgColor: 'bg-orange-100',
    subSteps: ['grader_profound', 'grader_rhetorical', 'grader_steady'],
    modalTitle: '评分详情',
  },
  {
    key: 'reviser',
    name: '修改员',
    nameCn: '修改员',
    icon: FileEdit,
    description: '正在根据意见修改文章...',
    color: 'text-pink-500',
    bgColor: 'bg-pink-100',
    modalTitle: '文章修订',
  },
  {
    key: 'reviewer',
    name: '审核员',
    nameCn: '审核员',
    icon: ShieldCheck,
    description: '正在进行最终质量审核...',
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-100',
    modalTitle: '审核报告',
  },
  {
    key: 'completed',
    name: '完成',
    nameCn: '完成',
    icon: CheckCircle,
    description: '生成完成！',
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-100',
    modalTitle: '生成结果',
  },
];

/**
 * Get the step index for an agent key
 */
function getStepIndex(agentKey) {
  if (!agentKey) return -1;

  // Check for exact match
  const exactIndex = AGENT_STEPS.findIndex((step) => step.key === agentKey);
  if (exactIndex >= 0) return exactIndex;

  // Check for sub-step match (writer_*, grader_*)
  for (let i = 0; i < AGENT_STEPS.length; i++) {
    const step = AGENT_STEPS[i];
    if (step.subSteps?.includes(agentKey)) {
      return i;
    }
  }

  // Handle aggregator -> completed
  if (agentKey === 'aggregator') return AGENT_STEPS.length - 1;

  return -1;
}

/**
 * Format intermediate data for display
 */
/**
 * Format intermediate data for display
 */
function formatIntermediateData(data, agentKey) {
  if (!data) return '暂无数据';

  // Handle Librarian Data (Materials)
  if (data.quotes || data.facts || data.theories || data.literature) {
    let md = '';
    const sectionMap = {
      quotes: '名言警句',
      facts: '事实论据',
      theories: '理论支撑',
      literature: '文学素材'
    };

    for (const [key, label] of Object.entries(sectionMap)) {
      if (data[key] && data[key].length > 0) {
        md += `### ${label}\n`;
        data[key].forEach(item => {
          md += `- ${item}\n`;
        });
        md += '\n';
      }
    }
    return md || '未检索到有效素材';
  }

  // Handle Outliner Data
  if (data.introduction && data.body && data.conclusion) {
    let md = `**结构类型**：${data.structure_type || '未定义'}\n\n`;

    // Introduction
    md += `### 第一部分：开头\n`;
    md += `- **开篇方式**：${data.introduction.method}\n`;
    md += `- **核心内容**：${data.introduction.content}\n`;
    md += `- **预计字数**：${data.introduction.word_count}字\n\n`;

    // Body
    md += `### 第二部分：主体\n`;
    data.body.forEach((item, index) => {
      md += `#### 分论点 ${index + 1}\n`;
      md += `- **论点**：${item.sub_thesis}\n`;
      md += `- **论证**：${item.method}\n`;
      if (item.materials && item.materials.length > 0) {
        md += `- **素材**：${item.materials.join('、')}\n`;
      }
      md += `\n`;
    });

    // Conclusion
    md += `### 第三部分：结尾\n`;
    md += `- **总结方式**：${data.conclusion.method}\n`;
    md += `- **升华方向**：${data.conclusion.elevation}\n`;

    return md;
  }

  // Handle Strategist Data (Analysis)
  if (data.analysis || (data.angle && data.thesis)) {
    let md = '';
    if (data.angle) md += `**立意角度**：${data.angle}\n\n`;
    if (data.thesis) md += `**中心论点**：${data.thesis}\n\n`;

    if (data.style_params) {
      md += `### 风格设计\n`;
      const styles = {
        profound: '深刻型',
        rhetorical: '文采型',
        steady: '稳健型'
      };

      for (const [key, name] of Object.entries(styles)) {
        if (data.style_params[key]) {
          const params = data.style_params[key];
          md += `#### ${name}\n`;
          if (typeof params === 'object') {
            if (params.focus) md += `- **侧重方向**：${params.focus}\n`;
            if (params.structure) md += `- **结构安排**：${params.structure}\n`;
            if (params.method) md += `- **论证手法**：${params.method}\n`;
            if (params.rhetoric && params.rhetoric.length > 0) md += `- **修辞手法**：${Array.isArray(params.rhetoric) ? params.rhetoric.join('、') : params.rhetoric}\n`;
            if (params.references && params.references.length > 0) md += `- **参考素材**：${Array.isArray(params.references) ? params.references.join('、') : params.references}\n`;
          } else {
            md += `${params}\n`;
          }
          md += '\n';
        }
      }
    }
    return md || JSON.stringify(data, null, 2);
  }

  // Fallback: Generic formatting
  if (typeof data === 'string') return data;

  if (Array.isArray(data)) {
    return data.map(item => `- ${typeof item === 'object' ? JSON.stringify(item) : item}`).join('\n');
  }

  if (typeof data === 'object') {
    return '```json\n' + JSON.stringify(data, null, 2) + '\n```';
  }

  return String(data);
}

/**
 * Intermediate Data Modal Component
 */
function IntermediateModal({ isOpen, onClose, title, data }) {
  if (!isOpen) return null;

  const formattedData = formatIntermediateData(data);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center space-x-2">
            <Eye className="w-5 h-5 text-indigo-600" />
            <h3 className="text-lg font-bold text-gray-900">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto">
          {data ? (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{formattedData}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              该步骤尚未完成，暂无数据
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t bg-gray-50 rounded-b-xl">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * ProgressStream Component
 *
 * Displays real-time progress of the essay generation workflow.
 * Shows a visual stepper with current agent status and a log window.
 * Icons are clickable to show intermediate outputs.
 */
function ProgressStream({ currentAgent, message, logs = [], isComplete, isError, intermediateData = {} }) {
  const logContainerRef = useRef(null);
  const currentStepIndex = getStepIndex(currentAgent);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalStep, setModalStep] = useState(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Handle step click
  const handleStepClick = (step, index) => {
    // Only allow clicking on completed steps or currently active step
    if (index <= currentStepIndex || isComplete) {
      setModalStep(step);
      setModalOpen(true);
    }
  };

  // Get data for a step
  const getStepData = (stepKey) => {
    const data = intermediateData[stepKey];
    if (data?.data) return data.data;
    return null;
  };

  return (
    <div className="card">
      {/* Intermediate Data Modal */}
      <IntermediateModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={modalStep?.modalTitle || '详情'}
        data={modalStep ? getStepData(modalStep.key) : null}
      />

      <div className="card-header">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">生成进度</h2>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          点击已完成的步骤图标可查看详情
        </p>
      </div>

      <div className="card-body">
        {/* Stepper */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            {AGENT_STEPS.map((step, index) => {
              const Icon = step.icon;
              const isActive = index === currentStepIndex && !isComplete && !isError;
              const isCompleted = index < currentStepIndex || isComplete;
              const isPending = index > currentStepIndex && !isComplete;
              const isClickable = isCompleted || (isActive && !isError);

              return (
                <div key={step.key} className="flex items-center flex-1">
                  {/* Step Circle */}
                  <div className="flex flex-col items-center">
                    <button
                      onClick={() => handleStepClick(step, index)}
                      disabled={!isClickable}
                      className={clsx(
                        'flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300',
                        isActive && `${step.bgColor} ${step.color} agent-pulse`,
                        isCompleted && 'bg-emerald-100 text-emerald-600 hover:bg-emerald-200 cursor-pointer',
                        isPending && 'bg-gray-100 text-gray-400 cursor-not-allowed',
                        isError && index === currentStepIndex && 'bg-red-100 text-red-600',
                        isClickable && !isActive && 'hover:ring-2 hover:ring-offset-2 hover:ring-indigo-400'
                      )}
                      title={isClickable ? `点击查看${step.nameCn}详情` : step.description}
                    >
                      {isActive && !isError ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : isError && index === currentStepIndex ? (
                        <AlertCircle className="w-5 h-5" />
                      ) : isCompleted ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        <Icon className="w-5 h-5" />
                      )}
                    </button>
                    <span
                      className={clsx(
                        'text-xs mt-2 font-medium text-center',
                        isActive && step.color,
                        isCompleted && 'text-emerald-600',
                        isPending && 'text-gray-400',
                        isError && index === currentStepIndex && 'text-red-600'
                      )}
                    >
                      {step.nameCn}
                    </span>
                  </div>

                  {/* Connector Line */}
                  {index < AGENT_STEPS.length - 1 && (
                    <div
                      className={clsx(
                        'flex-1 h-1 mx-2 rounded-full transition-all duration-500',
                        index < currentStepIndex || isComplete
                          ? 'bg-emerald-300'
                          : 'bg-gray-200'
                      )}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Current Status Message */}
        {message && (
          <div
            className={clsx(
              'p-4 rounded-lg mb-4',
              isError ? 'bg-red-50 border border-red-200' : 'bg-indigo-50 border border-indigo-200'
            )}
          >
            <div className="flex items-center">
              {!isComplete && !isError && (
                <Loader2 className="w-5 h-5 text-indigo-600 animate-spin mr-3" />
              )}
              {isComplete && <CheckCircle className="w-5 h-5 text-emerald-600 mr-3" />}
              {isError && <AlertCircle className="w-5 h-5 text-red-600 mr-3" />}
              <span
                className={clsx(
                  'font-medium',
                  isError ? 'text-red-700' : isComplete ? 'text-emerald-700' : 'text-indigo-700'
                )}
              >
                {message}
              </span>
            </div>
          </div>
        )}

        {/* Log Window */}
        {logs.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">活动日志</h3>
            <div
              ref={logContainerRef}
              className="bg-gray-900 rounded-lg p-4 h-48 overflow-y-auto scrollbar-thin font-mono text-sm"
            >
              {logs.map((log, index) => (
                <div key={index} className="flex items-start mb-2 last:mb-0">
                  <span className="text-gray-500 mr-2 flex-shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span
                    className={clsx(
                      'mr-2 flex-shrink-0',
                      log.type === 'error' ? 'text-red-400' : 'text-emerald-400'
                    )}
                  >
                    [{log.agent || 'system'}]
                  </span>
                  <span className="text-gray-300">{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProgressStream;
