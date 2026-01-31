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
} from 'lucide-react';
import clsx from 'clsx';

/**
 * Agent step configuration
 */
const AGENT_STEPS = [
  {
    key: 'strategist',
    name: 'Strategist',
    nameCn: 'Strategist',
    icon: Lightbulb,
    description: 'Analyzing topic and determining angle...',
    color: 'text-amber-500',
    bgColor: 'bg-amber-100',
  },
  {
    key: 'librarian',
    name: 'Librarian',
    nameCn: 'Librarian',
    icon: Search,
    description: 'Retrieving quotes and materials...',
    color: 'text-blue-500',
    bgColor: 'bg-blue-100',
  },
  {
    key: 'outliner',
    name: 'Outliner',
    nameCn: 'Outliner',
    icon: ListOrdered,
    description: 'Creating essay outline...',
    color: 'text-green-500',
    bgColor: 'bg-green-100',
  },
  {
    key: 'writer',
    name: 'Writers',
    nameCn: 'Writers',
    icon: PenTool,
    description: 'Writing three essay styles...',
    color: 'text-purple-500',
    bgColor: 'bg-purple-100',
    subSteps: ['writer_profound', 'writer_rhetorical', 'writer_steady'],
  },
  {
    key: 'grader',
    name: 'Graders',
    nameCn: 'Graders',
    icon: Star,
    description: 'Scoring and critiquing essays...',
    color: 'text-orange-500',
    bgColor: 'bg-orange-100',
    subSteps: ['grader_profound', 'grader_rhetorical', 'grader_steady'],
  },
  {
    key: 'completed',
    name: 'Complete',
    nameCn: 'Complete',
    icon: CheckCircle,
    description: 'Generation complete!',
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-100',
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
 * ProgressStream Component
 *
 * Displays real-time progress of the essay generation workflow.
 * Shows a visual stepper with current agent status and a log window.
 */
function ProgressStream({ currentAgent, message, logs = [], isComplete, isError }) {
  const logContainerRef = useRef(null);
  const currentStepIndex = getStepIndex(currentAgent);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">Generation Progress</h2>
        </div>
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

              return (
                <div key={step.key} className="flex items-center flex-1">
                  {/* Step Circle */}
                  <div className="flex flex-col items-center">
                    <div
                      className={clsx(
                        'flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300',
                        isActive && `${step.bgColor} ${step.color} agent-pulse`,
                        isCompleted && 'bg-emerald-100 text-emerald-600',
                        isPending && 'bg-gray-100 text-gray-400',
                        isError && index === currentStepIndex && 'bg-red-100 text-red-600'
                      )}
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
                    </div>
                    <span
                      className={clsx(
                        'text-xs mt-2 font-medium text-center',
                        isActive && step.color,
                        isCompleted && 'text-emerald-600',
                        isPending && 'text-gray-400',
                        isError && index === currentStepIndex && 'text-red-600'
                      )}
                    >
                      {step.name}
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
            <h3 className="text-sm font-medium text-gray-700 mb-2">Activity Log</h3>
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
