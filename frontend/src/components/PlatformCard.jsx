import React, { useState } from 'react';
import { Hash, X, Check, Globe2, Lock, EyeOff } from 'lucide-react';

const CHAR_LIMITS = {
  tiktok: 2200,
  threads: 500,
  facebook: 2200,
  youtube: 5000,
};

export default function PlatformCard({ platform, config, onChange }) {
  const [tagInput, setTagInput] = useState('');
  const limit = CHAR_LIMITS[platform.id] || 2200;
  const isEnabled = config.enabled ?? true;

  const updateField = (field, value) => {
    onChange({
      ...config,
      [field]: value,
    });
  };

  const handleToggleEnabled = (e) => {
    updateField('enabled', e.target.checked);
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

  const handleRemoveHashtag = (tagToRemove) => {
    const currentTags = config.hashtags || [];
    updateField(
      'hashtags',
      currentTags.filter((t) => t !== tagToRemove)
    );
  };

  return (
    <div
      className={`border rounded-xl transition-all ${
        isEnabled
          ? 'bg-slate-900 border-slate-700/80 shadow-md'
          : 'bg-slate-950/40 border-slate-800/60 opacity-60'
      }`}
    >
      {/* Card Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={handleToggleEnabled}
            className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700"
          />
          <span className="font-semibold text-slate-100 flex items-center gap-2 text-sm">
            {platform.name}
          </span>
        </label>

        <span className="text-[11px] font-mono text-slate-400">
          {(config.caption || '').length} / {limit} ký tự
        </span>
      </div>

      {/* Card Body */}
      <div className="p-4 space-y-4">
        {/* YouTube Specific: Title Input */}
        {platform.id === 'youtube' && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-slate-300">
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
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
            />
          </div>
        )}

        {/* Facebook Specific: Target Radio */}
        {platform.id === 'facebook' && (
          <div className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 space-y-2">
            <span className="text-xs font-medium text-slate-300 block mb-1">
              Nơi đăng Facebook:
            </span>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-300">
                <input
                  type="radio"
                  name="facebook_target"
                  value="profile"
                  checked={(config.target || 'profile') === 'profile'}
                  onChange={() => updateField('target', 'profile')}
                  disabled={!isEnabled}
                  className="text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700"
                />
                Trang cá nhân (Reel)
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-300">
                <input
                  type="radio"
                  name="facebook_target"
                  value="fanpage"
                  checked={config.target === 'fanpage'}
                  onChange={() => updateField('target', 'fanpage')}
                  disabled={!isEnabled}
                  className="text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700"
                />
                Fanpage
              </label>
            </div>
            {config.target === 'fanpage' && (
              <div className="pt-1">
                <label className="text-[11px] font-medium text-slate-400 block mb-1">
                  Page ID hoặc Page username (tùy chọn):
                </label>
                <input
                  type="text"
                  value={config.page_id || ''}
                  onChange={(e) => updateField('page_id', e.target.value)}
                  placeholder="Ví dụ: myfanpage hoặc 123456789 (để trống nếu dùng Business Suite)..."
                  disabled={!isEnabled}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                />
              </div>
            )}
          </div>
        )}

        {/* Caption Textarea */}
        <div>
          <label className="text-xs font-medium text-slate-300 block mb-1">
            {platform.id === 'youtube' ? 'Mô tả video' : 'Nội dung Caption'}
          </label>
          <textarea
            rows={3}
            maxLength={limit}
            value={config.caption || ''}
            onChange={(e) => updateField('caption', e.target.value)}
            placeholder={`Nhập caption đăng trên ${platform.name}...`}
            disabled={!isEnabled}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50 resize-y transition-colors"
          />
        </div>

        {/* Hashtags Section */}
        <div>
          <label className="text-xs font-medium text-slate-300 flex items-center gap-1 mb-1.5">
            <Hash className="w-3.5 h-3.5 text-indigo-400" />
            Hashtags / Tags
          </label>

          <div className="flex flex-wrap gap-1.5 mb-2">
            {(config.hashtags || []).map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 text-[11px] bg-slate-800/90 text-indigo-300 border border-slate-700 px-2 py-0.5 rounded-full"
              >
                #{tag}
                {isEnabled && (
                  <button
                    type="button"
                    onClick={() => handleRemoveHashtag(tag)}
                    className="hover:text-rose-400 p-0.5"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                )}
              </span>
            ))}
          </div>

          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={handleAddHashtag}
            placeholder="Nhập hashtag rồi gõ Enter..."
            disabled={!isEnabled}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
          />
        </div>

        {/* YouTube Specific: Visibility Selector */}
        {platform.id === 'youtube' && (
          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">
              Chế độ hiển thị YouTube
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'public', label: 'Công khai', icon: Globe2 },
                { id: 'unlisted', label: 'Không công khai', icon: EyeOff },
                { id: 'private', label: 'Riêng tư', icon: Lock },
              ].map((item) => {
                const Icon = item.icon;
                const isSelected = (config.visibility || 'public') === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => updateField('visibility', item.id)}
                    disabled={!isEnabled}
                    className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium border transition-colors ${
                      isSelected
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {item.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
