import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Loader2, AlertCircle, Wand2, Lightbulb } from 'lucide-react';

const QUICK_TOPICS = [
  '🔥 3 mẹo công nghệ cực tiện lợi',
  '☕ Review quán cà phê chill cuối tuần',
  '💡 Bài học phát triển bản thân mỗi ngày',
  '🚀 Xu hướng AI & kiếm tiền online',
  '🎬 Hậu trường một ngày làm việc sáng tạo',
];

export default function AIPromptSection({ onGenerated }) {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
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

  const handleSelectQuickTopic = (suggestedTopic) => {
    // Strip leading emoji for clean prompt
    const cleaned = suggestedTopic.replace(/^[^\w\s\dÀ-ỹ]+/, '').trim();
    setTopic(cleaned);
    setError(null);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className={`bg-slate-900/90 backdrop-blur-xl border rounded-2xl p-5 shadow-xl relative overflow-hidden transition-all ${
        loading ? 'border-indigo-500/60 shadow-indigo-500/20 shadow-lg' : 'border-slate-800/80'
      }`}
    >
      {/* Background ambient lighting */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between mb-3 relative z-10">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
              Trợ Lý AI Soạn Caption
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Gemini 2.5
              </span>
            </h2>
            <p className="text-[11px] text-slate-400">
              Tự động hóa văn phong riêng biệt cho TikTok, Threads, FB & Shorts
            </p>
          </div>
        </div>
      </div>

      {/* Quick Topic Chips */}
      <div className="mb-3.5 relative z-10">
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-medium mb-2">
          <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
          <span>Gợi ý chủ đề nhanh:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_TOPICS.map((item, index) => (
            <motion.button
              key={index}
              whileHover={{ scale: 1.04, y: -1 }}
              whileTap={{ scale: 0.96 }}
              type="button"
              onClick={() => handleSelectQuickTopic(item)}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-950/70 hover:bg-indigo-950/40 text-slate-300 hover:text-indigo-300 border border-slate-800/80 hover:border-indigo-500/30 transition-all text-left"
            >
              {item}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Error Alert */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3.5 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs flex items-center gap-2 overflow-hidden"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="flex-1">{error}</span>
            <button
              onClick={() => setError(null)}
              className="text-[10px] text-rose-300 hover:underline"
            >
              Đóng
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Form Input */}
      <form onSubmit={handleGenerate} className="space-y-3 relative z-10">
        <div className="relative">
          <textarea
            rows={3}
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Nhập ý tưởng / chủ đề video (ví dụ: 3 mẹo tiết kiệm tiền cho sinh viên, review quán cà phê phong cách vintage...)"
            className="w-full bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none transition-all"
          />
          {topic && (
            <button
              type="button"
              onClick={() => setTopic('')}
              className="absolute top-2.5 right-2.5 text-[10px] text-slate-500 hover:text-slate-300 bg-slate-800 px-1.5 py-0.5 rounded"
            >
              Xóa
            </button>
          )}
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          type="submit"
          disabled={loading || !topic.trim()}
          className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 hover:from-indigo-600 hover:via-purple-700 hover:to-pink-600 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span>Gemini đang phân tích & viết caption...</span>
            </>
          ) : (
            <>
              <Wand2 className="w-4 h-4 text-amber-300" />
              <span>✨ Tạo Caption bằng AI</span>
            </>
          )}
        </motion.button>
      </form>
    </motion.div>
  );
}
