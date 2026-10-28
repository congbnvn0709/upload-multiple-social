import React, { useState } from 'react';
import { Sparkles, Loader2, AlertCircle } from 'lucide-react';

export default function AIPromptSection({ onGenerated }) {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!topic.trim()) {
      setError('Vui lòng nhập chủ đề hoặc ý tưởng video');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await fetch('/api/ai/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic.trim() }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Không thể tạo nội dung AI');
      }

      const data = await res.json();
      if (onGenerated) {
        onGenerated(data);
      }
    } catch (err) {
      console.error('AI generate error:', err);
      setError(err.message || 'Lỗi khi gọi AI Gemini');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-5 h-5 text-amber-400" />
        <h2 className="text-base font-semibold text-white">
          Trợ Lý AI Soạn Caption
        </h2>
      </div>

      <p className="text-xs text-slate-400 mb-3 leading-relaxed">
        Nhập ý tưởng ngắn về nội dung video, Gemini sẽ tự động tạo caption, hashtag và tiêu đề tối ưu cho từng nền tảng.
      </p>

      {error && (
        <div className="mb-3 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleGenerate} className="space-y-3">
        <textarea
          rows={3}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Nhập ý tưởng / chủ đề video (ví dụ: 3 mẹo tiết kiệm tiền cho sinh viên, review quán cà phê phong cách vintage...)"
          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none transition-colors"
        />

        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:from-indigo-600 hover:via-purple-600 hover:to-pink-600 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Đang tạo nội dung thông minh...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>✨ Tạo Caption bằng AI</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
