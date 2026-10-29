import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Hash, X, Check, Globe2, Lock, EyeOff, Copy, CheckCheck, 
  Sparkles, Plus, Share2, Video, ChevronRight, AtSign
} from 'lucide-react';

const CHAR_LIMITS = {
  tiktok: 2200,
  threads: 500,
  facebook: 2200,
  youtube: 5000,
};

const POPULAR_TAGS = {
  tiktok: ['fyp', 'xuhuong', 'viral', 'trend'],
  threads: ['tech', 'thoughts', 'creators', 'vietnam'],
  facebook: ['reels', 'viralreels', 'xuhuong', 'chiase'],
  youtube: ['Shorts', 'trending', 'review', 'viralvideo'],
};

export default function PlatformCard({ platform, config, onChange }) {
  const [tagInput, setTagInput] = useState('');
  const [copied, setCopied] = useState(false);
  const limit = CHAR_LIMITS[platform.id] || 2200;
  const isEnabled = config.enabled ?? true;
  const captionLength = (config.caption || '').length;
  const lengthPercentage = Math.min(100, Math.round((captionLength / limit) * 100));

  const updateField = (field, value) => {
    onChange({
      ...config,
      [field]: value,
    });
  };

  const handleToggleEnabled = (newVal) => {
    updateField('enabled', newVal);
  };

  const handleAddHashtag = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const rawTag = tagInput.trim().replace(/^#/, '');
      if (rawTag) {
        const currentTags = config.hashtags || [];
        if (!currentTags.includes(rawTag)) {
          updateField('hashtags', [...currentTags, rawTag]);
        }
      }
      setTagInput('');
    }
  };

  const handleAddQuickTag = (tag) => {
    const currentTags = config.hashtags || [];
    if (!currentTags.includes(tag)) {
      updateField('hashtags', [...currentTags, tag]);
    }
  };

  const handleRemoveHashtag = (tagToRemove) => {
    const currentTags = config.hashtags || [];
    updateField(
      'hashtags',
      currentTags.filter((t) => t !== tagToRemove)
    );
  };

  const handleCopyCaption = () => {
    const fullText = `${config.caption || ''}\n\n${(config.hashtags || [])
      .map((t) => `#${t}`)
      .join(' ')}`.trim();
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      layout
      whileHover={isEnabled ? { y: -2, transition: { duration: 0.2 } } : {}}
      className={`border rounded-2xl transition-all relative overflow-hidden backdrop-blur-xl ${
        isEnabled
          ? 'bg-slate-900/90 border-slate-700/80 shadow-lg shadow-black/20'
          : 'bg-slate-950/40 border-slate-800/60 opacity-60'
      }`}
    >
      {/* Top Brand Accent Line */}
      <div className={`h-1 w-full bg-gradient-to-r ${platform.activeGradient || 'from-indigo-500 to-purple-500'} ${isEnabled ? 'opacity-100' : 'opacity-20'}`} />

      {/* Card Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={(e) => handleToggleEnabled(e.target.checked)}
            className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700 cursor-pointer"
          />
          <span className="font-semibold text-slate-100 flex items-center gap-2 text-sm">
            {platform.name}
          </span>
        </label>

        <div className="flex items-center gap-2">
          {/* Quick Copy Action */}
          {isEnabled && (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={handleCopyCaption}
              className="p-1.5 text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 rounded-lg transition-colors text-xs"
              title="Sao chép toàn bộ caption"
            >
              {copied ? (
                <CheckCheck className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </motion.button>
          )}

          {/* Character counter */}
          <span className={`text-[11px] font-mono px-2 py-0.5 rounded-md ${
            lengthPercentage > 90 
              ? 'text-rose-400 bg-rose-500/10' 
              : 'text-slate-400 bg-slate-950/60'
          }`}>
            {captionLength} / {limit}
          </span>
        </div>
      </div>

      {/* Card Body */}
      <div className="p-4 space-y-4">
        {/* YouTube Specific: Title Input */}
        {platform.id === 'youtube' && (
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 text-red-400" />
                Tiêu đề video Shorts
              </label>
              <span className="text-[10px] text-slate-500 font-mono">
                {(config.title || '').length} / 100
              </span>
            </div>
            <input
              type="text"
              maxLength={100}
              value={config.title || ''}
              onChange={(e) => updateField('title', e.target.value)}
              placeholder="Tiêu đề YouTube Shorts hấp dẫn (tối đa 100 ký tự)..."
              disabled={!isEnabled}
              className="w-full bg-slate-950/90 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500/70 focus:ring-1 focus:ring-red-500/50 disabled:opacity-50 transition-all"
            />
          </div>
        )}

        {/* Facebook Specific: Profile vs Fanpage Target Selector */}
        {platform.id === 'facebook' && (
          <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-2.5">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Share2 className="w-3.5 h-3.5 text-blue-400" />
              Đích đến đăng bài:
            </label>
            <div className="flex flex-wrap gap-2 text-xs">
              <label className="flex items-center gap-2 cursor-pointer bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700">
                <input
                  type="radio"
                  name="facebook_target"
                  value="profile"
                  checked={(config.target || 'profile') === 'profile'}
                  onChange={() => updateField('target', 'profile')}
                  disabled={!isEnabled}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <span className="text-slate-300">Trang cá nhân (Reel)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700">
                <input
                  type="radio"
                  name="facebook_target"
                  value="fanpage"
                  checked={config.target === 'fanpage'}
                  onChange={() => updateField('target', 'fanpage')}
                  disabled={!isEnabled}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <span className="text-slate-300">Fanpage Facebook</span>
              </label>
            </div>

            {config.target === 'fanpage' && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="pt-1"
              >
                <div className="flex items-center gap-1 mb-1 text-[11px] text-slate-400">
                  <AtSign className="w-3 h-3 text-blue-400" />
                  <span>ID hoặc Tên Người Dùng Trang (tùy chọn):</span>
                </div>
                <input
                  type="text"
                  value={config.page_id || ''}
                  onChange={(e) => updateField('page_id', e.target.value)}
                  placeholder="Ví dụ: myfanpage hoặc để trống mở Business Suite"
                  disabled={!isEnabled}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </motion.div>
            )}
          </div>
        )}

        {/* Main Caption Editor */}
        <div>
          <label className="text-xs font-medium text-slate-300 block mb-1.5">
            {platform.id === 'youtube' ? 'Mô tả video & từ khóa' : 'Nội dung Caption bài viết'}
          </label>
          <textarea
            rows={platform.id === 'threads' ? 3 : 4}
            value={config.caption || ''}
            onChange={(e) => updateField('caption', e.target.value)}
            placeholder={`Soạn thảo caption cho ${platform.name}...`}
            disabled={!isEnabled}
            className="w-full bg-slate-950/90 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/70 focus:ring-1 focus:ring-indigo-500/50 resize-none disabled:opacity-50 transition-all font-sans leading-relaxed"
          />
        </div>

        {/* Hashtags Section */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1">
              <Hash className="w-3.5 h-3.5 text-indigo-400" />
              Hashtags ({ (config.hashtags || []).length })
            </label>

            {/* Quick Popular Tags */}
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-slate-500">Gợi ý:</span>
              {(POPULAR_TAGS[platform.id] || []).map((ptag) => (
                <button
                  key={ptag}
                  type="button"
                  onClick={() => handleAddQuickTag(ptag)}
                  disabled={!isEnabled || (config.hashtags || []).includes(ptag)}
                  className="text-[10px] text-slate-400 hover:text-indigo-300 disabled:opacity-30 transition-colors"
                >
                  #{ptag}
                </button>
              ))}
            </div>
          </div>

          {/* Hashtag Pills */}
          <div className="flex flex-wrap gap-1.5 mb-2 min-h-[28px] p-2 bg-slate-950/60 rounded-xl border border-slate-800/80 items-center">
            <AnimatePresence>
              {(config.hashtags || []).map((tag) => (
                <motion.span
                  key={tag}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[11px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/25 shadow-sm"
                >
                  <span>#{tag}</span>
                  {isEnabled && (
                    <button
                      type="button"
                      onClick={() => handleRemoveHashtag(tag)}
                      className="hover:text-rose-400 ml-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </motion.span>
              ))}
            </AnimatePresence>

            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleAddHashtag}
              placeholder="+ Thêm thẻ (Enter)..."
              disabled={!isEnabled}
              className="bg-transparent text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none px-1 py-0.5 flex-1 min-w-[100px] disabled:opacity-50"
            />
          </div>
        </div>

        {/* YouTube Specific: Visibility Selector */}
        {platform.id === 'youtube' && (
          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Globe2 className="w-3.5 h-3.5 text-red-400" />
              Chế độ hiển thị:
            </span>
            <select
              value={config.visibility || 'public'}
              onChange={(e) => updateField('visibility', e.target.value)}
              disabled={!isEnabled}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-red-500"
            >
              <option value="public">Công khai (Public)</option>
              <option value="unlisted">Không công khai (Unlisted)</option>
              <option value="private">Riêng tư (Private)</option>
            </select>
          </div>
        )}
      </div>

      {/* Visual Character Usage Bar */}
      <div className="h-0.5 w-full bg-slate-800">
        <motion.div
          animate={{ width: `${lengthPercentage}%` }}
          transition={{ duration: 0.3 }}
          className={`h-full ${
            lengthPercentage > 90 ? 'bg-rose-500' : 'bg-indigo-500/70'
          }`}
        />
      </div>
    </motion.div>
  );
}
