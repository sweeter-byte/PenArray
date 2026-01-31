import { useState, useRef } from 'react';
import { Send, ImagePlus, X, Loader2, FileText } from 'lucide-react';
import clsx from 'clsx';

/**
 * TaskInput Component
 *
 * Form for submitting essay generation tasks.
 * Accepts text prompt and optional image upload.
 */
function TaskInput({ onSubmit, isLoading, disabled }) {
  const [prompt, setPrompt] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileInputRef = useRef(null);

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
      }

      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('Image size must be less than 5MB');
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

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!prompt.trim() && !imageFile) {
      alert('Please enter an essay topic or upload an image');
      return;
    }

    onSubmit({
      prompt: prompt.trim(),
      imageFile,
    });
  };

  const isDisabled = disabled || isLoading;

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center space-x-2">
          <FileText className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">Essay Generation Workbench</h2>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Enter a Gaokao essay topic or upload an image containing the prompt
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card-body space-y-4">
        {/* Text Prompt Input */}
        <div>
          <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
            Essay Topic
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
            placeholder="Enter the essay topic here...&#10;&#10;Example: According to the reading material, regarding 'Lying Flat' vs 'Involution' as a dialectical thinking exercise..."
          />
          <div className="flex justify-between mt-2">
            <span className="text-xs text-gray-400">
              Enter the Gaokao essay prompt for generation
            </span>
            <span className="text-xs text-gray-400">
              {prompt.length}/2000
            </span>
          </div>
        </div>

        {/* Image Upload Section */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Or Upload Topic Image (Optional)
          </label>

          {/* Image Preview */}
          {imagePreview ? (
            <div className="relative inline-block">
              <img
                src={imagePreview}
                alt="Topic preview"
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
                <span className="text-sm">Click to upload an image</span>
                <span className="text-xs text-gray-400 mt-1">PNG, JPG up to 5MB</span>
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
                Generating...
              </>
            ) : (
              <>
                <Send className="w-5 h-5 mr-2" />
                Generate Essays
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default TaskInput;
