import { useState } from 'react';
import { BookOpen, Star, MessageSquare, ChevronDown, ChevronUp, Trophy, Download, FileText, File } from 'lucide-react';
import clsx from 'clsx';
import ReactMarkdown from 'react-markdown';
import { exportApi } from '../api/client';

/**
 * Style configuration for essay cards (Localized to Chinese)
 */
const STYLE_CONFIG = {
  profound: {
    name: '深刻型',
    nameCn: '深刻型',
    description: '哲学思辨与逻辑严密',
    borderColor: 'border-t-purple-600',
    badgeClass: 'bg-purple-100 text-purple-700',
    scoreClass: 'bg-purple-500',
    icon: '????',
  },
  rhetorical: {
    name: '文采型',
    nameCn: '文采型',
    description: '文学素养与修辞华丽',
    borderColor: 'border-t-cyan-600',
    badgeClass: 'bg-cyan-100 text-cyan-700',
    scoreClass: 'bg-cyan-500',
    icon: '????',
  },
  steady: {
    name: '稳健型',
    nameCn: '稳健型',
    description: '结构工整与质量稳定',
    borderColor: 'border-t-green-600',
    badgeClass: 'bg-green-100 text-green-700',
    scoreClass: 'bg-green-500',
    icon: '????',
  },
};

/**
 * Get score grade description (Localized to Chinese)
 */
function getGradeLevel(score) {
  if (score >= 50) return { level: '一等文', color: 'text-yellow-600' };
  if (score >= 40) return { level: '二等文', color: 'text-blue-600' };
  if (score >= 30) return { level: '三等文', color: 'text-gray-600' };
  return { level: '四等文', color: 'text-red-600' };
}

/**
 * Single Essay Card Component
 */
function EssayCard({ essay, isBestScore }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showCritique, setShowCritique] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const config = STYLE_CONFIG[essay.style] || STYLE_CONFIG.steady;
  const grade = essay.score ? getGradeLevel(essay.score) : null;

  const handleDownload = async (format) => {
    if (!essay.id) {
      alert('作文ID不存在，无法下载');
      return;
    }
    setIsDownloading(true);
    try {
      if (format === 'docx') {
        await exportApi.downloadDocx(essay.id);
      } else {
        await exportApi.downloadPdf(essay.id);
      }
    } catch (err) {
      console.error('Download failed:', err);
      alert('下载失败，请重试');
    } finally {
      setIsDownloading(false);
    }
  };

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
              {config.nameCn}
            </span>
            {isBestScore && (
              <span className="flex items-center text-yellow-600 text-sm">
                <Trophy className="w-4 h-4 mr-1" />
                最佳
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
                <div className="text-xs text-gray-500">/60分</div>
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

        {/* Download Buttons */}
        <div className="mt-3 flex items-center space-x-2">
          <button
            onClick={() => handleDownload('docx')}
            disabled={isDownloading}
            className="flex items-center px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
            title="下载Word文档"
          >
            <FileText className="w-3.5 h-3.5 mr-1" />
            下载Word
          </button>
          <button
            onClick={() => handleDownload('pdf')}
            disabled={isDownloading}
            className="flex items-center px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50"
            title="下载PDF文档"
          >
            <File className="w-3.5 h-3.5 mr-1" />
            下载PDF
          </button>
        </div>
      </div>

      {/* Expand/Collapse Toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-5 py-2 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <span className="text-sm text-gray-600">
          {isExpanded ? '收起正文' : '展开正文'}
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
            <ReactMarkdown
              className="prose prose-sm max-w-none prose-p:my-2 prose-headings:font-bold prose-headings:text-gray-900 prose-ul:list-disc prose-ul:pl-4"
            >
              {(() => {
                // Remove the first line if it's a markdown header or bold title to avoid duplication
                let content = essay.content || '';
                let lines = content.trim().split('\n');

                // Remove empty leading lines
                while (lines.length > 0 && !lines[0].trim()) {
                  lines.shift();
                }

                if (lines.length > 0) {
                  const firstLine = lines[0].trim();
                  // Check for # Header or **Bold Title** or just a short line acting as title
                  // Criteria: Starts with # OR (Starts with ** AND Ends with **) OR (Short length < 30)
                  const isHeader = firstLine.startsWith('#');
                  const isBoldTitle = firstLine.startsWith('**') && firstLine.endsWith('**') && firstLine.length < 50;
                  const isShortTitle = firstLine.length < 30 && !firstLine.includes('。'); // Short and not a sentence

                  if (isHeader || isBoldTitle || isShortTitle) {
                    // Check if it's really the title (fuzzy match or just assume context)
                    // For safety, we only remove if it's clearly a header-like structure
                    // The user explicitly complained about duplicate titles, so we can be slightly aggressive
                    return lines.slice(1).join('\n').trim();
                  }
                }
                return content;
              })()}
            </ReactMarkdown>
          </div>

          {/* Word Count */}
          <div className="mt-4 text-xs text-gray-400">
            字数统计：{essay.content?.length || 0} 字
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
              <span className="text-sm font-medium">阅卷评语</span>
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
                <ReactMarkdown
                  className="prose prose-sm max-w-none prose-p:my-1 prose-headings:font-bold prose-headings:text-amber-900 prose-ul:list-disc prose-ul:pl-4 prose-strong:text-amber-900 text-amber-800"
                >
                  {essay.critique}
                </ReactMarkdown>
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
          <h2 className="text-xl font-bold text-gray-900">生成作文</h2>
        </div>

        <div className="flex items-center space-x-6 text-sm">
          <div className="flex items-center">
            <Star className="w-4 h-4 text-yellow-500 mr-1" />
            <span className="text-gray-600">
              最高分：<span className="font-semibold text-gray-900">{bestScore}</span>/60
            </span>
          </div>
          <div className="text-gray-600">
            平均分：<span className="font-semibold text-gray-900">{avgScore.toFixed(1)}</span>/60
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
