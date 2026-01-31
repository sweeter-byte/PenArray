import { useState } from 'react';
import { BookOpen, Star, MessageSquare, ChevronDown, ChevronUp, Trophy } from 'lucide-react';
import clsx from 'clsx';

/**
 * Style configuration for essay cards
 */
const STYLE_CONFIG = {
  profound: {
    name: 'Profound',
    nameCn: 'Profound',
    description: 'Philosophical depth and logical rigor',
    borderColor: 'border-t-purple-600',
    badgeClass: 'bg-purple-100 text-purple-700',
    scoreClass: 'bg-purple-500',
    icon: '????',
  },
  rhetorical: {
    name: 'Rhetorical',
    nameCn: 'Rhetorical',
    description: 'Literary elegance and rhetorical flourish',
    borderColor: 'border-t-cyan-600',
    badgeClass: 'bg-cyan-100 text-cyan-700',
    scoreClass: 'bg-cyan-500',
    icon: '????',
  },
  steady: {
    name: 'Steady',
    nameCn: 'Steady',
    description: 'Reliable structure and consistent quality',
    borderColor: 'border-t-green-600',
    badgeClass: 'bg-green-100 text-green-700',
    scoreClass: 'bg-green-500',
    icon: '????',
  },
};

/**
 * Get score grade description
 */
function getGradeLevel(score) {
  if (score >= 50) return { level: 'First Class', color: 'text-yellow-600' };
  if (score >= 40) return { level: 'Second Class', color: 'text-blue-600' };
  if (score >= 30) return { level: 'Third Class', color: 'text-gray-600' };
  return { level: 'Fourth Class', color: 'text-red-600' };
}

/**
 * Single Essay Card Component
 */
function EssayCard({ essay, isBestScore }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showCritique, setShowCritique] = useState(false);

  const config = STYLE_CONFIG[essay.style] || STYLE_CONFIG.steady;
  const grade = essay.score ? getGradeLevel(essay.score) : null;

  return (
    <div
      className={clsx(
        'card overflow-hidden border-t-4 transition-all duration-300',
        config.borderColor,
        isBestScore && 'ring-2 ring-yellow-400 ring-offset-2'
      )}
    >
      {/* Card Header */}
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className={clsx('px-3 py-1 rounded-full text-sm font-medium', config.badgeClass)}>
              {config.name}
            </span>
            {isBestScore && (
              <span className="flex items-center text-yellow-600 text-sm">
                <Trophy className="w-4 h-4 mr-1" />
                Best
              </span>
            )}
          </div>

          {/* Score Badge */}
          {essay.score !== null && essay.score !== undefined && (
            <div className="flex items-center space-x-2">
              <div
                className={clsx(
                  'flex items-center justify-center w-12 h-12 rounded-full text-white font-bold',
                  config.scoreClass
                )}
              >
                {essay.score}
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500">/60</div>
                {grade && (
                  <div className={clsx('text-xs font-medium', grade.color)}>{grade.level}</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Essay Title */}
        {essay.title && (
          <h3 className="mt-3 text-lg font-semibold text-gray-900">{essay.title}</h3>
        )}
      </div>

      {/* Expand/Collapse Toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-5 py-2 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <span className="text-sm text-gray-600">
          {isExpanded ? 'Hide Content' : 'Show Content'}
        </span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* Essay Content */}
      {isExpanded && (
        <div className="p-5">
          <div className="essay-content text-sm leading-7 max-h-96 overflow-y-auto scrollbar-thin">
            {essay.content}
          </div>

          {/* Word Count */}
          <div className="mt-4 text-xs text-gray-400">
            Word Count: {essay.content?.length || 0} characters
          </div>
        </div>
      )}

      {/* Critique Section */}
      {essay.critique && (
        <div className="border-t border-gray-100">
          <button
            onClick={() => setShowCritique(!showCritique)}
            className="w-full px-5 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center text-gray-700">
              <MessageSquare className="w-4 h-4 mr-2" />
              <span className="text-sm font-medium">Grader Comments</span>
            </div>
            {showCritique ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {showCritique && (
            <div className="px-5 pb-5">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-sm text-amber-800 whitespace-pre-wrap">{essay.critique}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * EssayComparison Component
 *
 * Displays three essays side-by-side in a 3-column grid layout.
 * Shows scores with tooltips for critique on hover.
 */
function EssayComparison({ essays }) {
  if (!essays || essays.length === 0) {
    return null;
  }

  // Sort essays by style order
  const styleOrder = ['profound', 'rhetorical', 'steady'];
  const sortedEssays = [...essays].sort(
    (a, b) => styleOrder.indexOf(a.style) - styleOrder.indexOf(b.style)
  );

  // Find best score
  const bestScore = Math.max(...essays.map((e) => e.score || 0));
  const avgScore = essays.reduce((sum, e) => sum + (e.score || 0), 0) / essays.length;

  return (
    <div>
      {/* Header with Stats */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-6 h-6 text-indigo-600" />
          <h2 className="text-xl font-bold text-gray-900">Generated Essays</h2>
        </div>

        <div className="flex items-center space-x-6 text-sm">
          <div className="flex items-center">
            <Star className="w-4 h-4 text-yellow-500 mr-1" />
            <span className="text-gray-600">
              Best Score: <span className="font-semibold text-gray-900">{bestScore}</span>/60
            </span>
          </div>
          <div className="text-gray-600">
            Average: <span className="font-semibold text-gray-900">{avgScore.toFixed(1)}</span>/60
          </div>
        </div>
      </div>

      {/* 3-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {sortedEssays.map((essay) => (
          <EssayCard
            key={essay.id || essay.style}
            essay={essay}
            isBestScore={essay.score === bestScore && bestScore > 0}
          />
        ))}
      </div>
    </div>
  );
}

export default EssayComparison;
