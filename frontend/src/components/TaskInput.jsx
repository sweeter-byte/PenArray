import { useState, useRef, useEffect } from 'react';
import { Send, ImagePlus, X, Loader2, FileText, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import clsx from 'clsx';

// Advanced structure template from requirements
const ADVANCED_STRUCTURE_TEMPLATE = `标题使用对仗式，每半句4~6字；首段130~170字，需要联系作文题目给的材料，必须阐释清自己的观点，点题，包含关键字词；后续围绕总论点写三个分论点，每个分论点占一个自然段；每段开头必须提出分论点，并结合常用的议论方式进行阐释，例如举例论证；对于举例论证，可以使用"排例"，就是把三个与分论点相关的人物事迹等写成排比句，气势磅礴，也可以对一个典型事例进行详细阐释说明，结合其他的论证手法等。需保证每一个分论点的论述方法都不太一样。结尾段需要收束全文，可以引用名人名言，加入"时代青年"的视角，提出新做法，并点题。`;

/**
 * TaskInput Component
 *
 * Form for submitting essay generation tasks.
 * Accepts text prompt, optional image upload, and custom structure constraints.
 */
function TaskInput({ onSubmit, isLoading, disabled, initialPrompt = '' }) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customStructure, setCustomStructure] = useState('');
  const fileInputRef = useRef(null);

  // Restore prompt if initialPrompt changes
  useEffect(() => {
    if (initialPrompt) {
      setPrompt(initialPrompt);
    }
  }, [initialPrompt]);

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert('请选择图片文件');
        return;
      }

      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('图片大小不能超过5MB');
        return;
      }

      setImageFile(file);

      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target?.result);
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const loadTemplate = () => {
    setCustomStructure(ADVANCED_STRUCTURE_TEMPLATE);
    setShowAdvanced(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!prompt.trim() && !imageFile) {
      alert('请输入作文题目或上传题目图片');
      return;
    }

    onSubmit({
      prompt: prompt.trim(),
      imageFile,
      customStructure: customStructure.trim() || null,
    });
  };

  const isDisabled = disabled || isLoading;

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center space-x-2">
          <FileText className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">作文生成工作台</h2>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          输入高考作文题目或上传题目图片，系统将生成三种不同风格的作文
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card-body space-y-4">
        {/* Text Prompt Input */}
        <div>
          <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
            作文题目
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isDisabled}
            rows={5}
            maxLength={2000}
            className={clsx(
              'input resize-none',
              isDisabled && 'bg-gray-50 cursor-not-allowed'
            )}
            placeholder="请在此输入作文题目...&#10;&#10;示例：阅读下面的材料，根据要求写作。关于'躺平'与'内卷'的辩证思考..."
          />
          <div className="flex justify-between mt-2">
            <span className="text-xs text-gray-400">
              输入高考作文题目，系统将自动生成三种风格的作文
            </span>
            <span className="text-xs text-gray-400">
              {prompt.length}/2000
            </span>
          </div>
        </div>

        {/* Image Upload Section */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            或上传题目图片（可选）
          </label>

          {/* Image Preview */}
          {imagePreview ? (
            <div className="relative inline-block">
              <img
                src={imagePreview}
                alt="题目预览"
                className="max-h-40 rounded-lg border border-gray-200"
              />
              <button
                type="button"
                onClick={removeImage}
                disabled={isDisabled}
                className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isDisabled}
              className={clsx(
                'flex items-center justify-center w-full py-6 border-2 border-dashed rounded-lg transition-colors',
                isDisabled
                  ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
                  : 'border-gray-300 hover:border-indigo-400 hover:bg-indigo-50'
              )}
            >
              <div className="flex flex-col items-center text-gray-500">
                <ImagePlus className="w-8 h-8 mb-2" />
                <span className="text-sm">点击上传图片</span>
                <span className="text-xs text-gray-400 mt-1">支持 PNG、JPG 格式，最大 5MB</span>
              </div>
            </button>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            className="hidden"
          />
        </div>

        {/* Advanced Options Toggle */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            {showAdvanced ? (
              <ChevronUp className="w-4 h-4 mr-1" />
            ) : (
              <ChevronDown className="w-4 h-4 mr-1" />
            )}
            高级选项：结构约束
          </button>
        </div>

        {/* Custom Structure Constraints (Advanced) */}
        {showAdvanced && (
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                结构约束（可选）
              </label>
              <button
                type="button"
                onClick={loadTemplate}
                disabled={isDisabled}
                className="flex items-center px-3 py-1 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5 mr-1" />
                加载高级模板
              </button>
            </div>
            <textarea
              value={customStructure}
              onChange={(e) => setCustomStructure(e.target.value)}
              disabled={isDisabled}
              rows={4}
              maxLength={1000}
              className={clsx(
                'input resize-none text-sm',
                isDisabled && 'bg-white cursor-not-allowed'
              )}
              placeholder="输入自定义的结构约束，例如：标题使用对仗式，首段需点题..."
            />
            <p className="mt-2 text-xs text-gray-400">
              这些约束将指导写手按照您的要求组织文章结构。留空则使用默认结构。
            </p>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end pt-4 border-t border-gray-100">
          <button
            type="submit"
            disabled={isDisabled || (!prompt.trim() && !imageFile)}
            className={clsx(
              'btn-primary px-6 py-3',
              (isDisabled || (!prompt.trim() && !imageFile)) && 'opacity-50 cursor-not-allowed'
            )}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                正在生成...
              </>
            ) : (
              <>
                <Send className="w-5 h-5 mr-2" />
                开始生成
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default TaskInput;
