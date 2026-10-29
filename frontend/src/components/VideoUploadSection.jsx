import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Film, Trash2, CheckCircle2, AlertCircle, Play, Sparkles, FileVideo, RefreshCw } from 'lucide-react';

function formatBytes(bytes, decimals = 2) {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export default function VideoUploadSection({ video, onVideoChange }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleUploadFile = async (file) => {
    if (!file) return;

    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (ext !== '.mp4' && ext !== '.mov') {
      setError('Chỉ hỗ trợ định dạng video .mp4 hoặc .mov');
      return;
    }

    setError(null);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Tải video lên thất bại');
      }

      const data = await res.json();
      onVideoChange(data);
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Lỗi khi tải video lên server');
    } finally {
      setUploading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleUploadFile(e.target.files[0]);
    }
  };

  const handleRemove = () => {
    onVideoChange(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-slate-900/90 backdrop-blur-xl border border-slate-800/80 rounded-2xl p-5 shadow-xl relative overflow-hidden group"
    >
      {/* Subtle background ambient corner glow */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between mb-4 relative z-10">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Film className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white tracking-tight">
              Tải Video Lên
            </h2>
            <p className="text-[11px] text-slate-400">
              Định dạng tối ưu 9:16 (Shorts, Reels, TikTok)
            </p>
          </div>
        </div>

        <AnimatePresence>
          {video && (
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-1.5 text-xs text-emerald-300 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/30 font-medium shadow-sm"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Sẵn sàng đăng
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Error Alert */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs flex items-center gap-2 overflow-hidden"
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

      {/* Video Preview or Drag & Drop Area */}
      <AnimatePresence mode="wait">
        {video ? (
          <motion.div
            key="video-preview"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="space-y-3"
          >
            {/* HTML5 Video Player */}
            <div className="relative rounded-xl overflow-hidden bg-black/80 border border-slate-800 shadow-inner group/video aspect-[9/16] max-h-[360px] mx-auto flex items-center justify-center">
              <video
                controls
                playsInline
                src={video.stream_url}
                className="w-full h-full object-contain"
              />
              <div className="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-md text-[10px] text-slate-300 font-mono border border-white/10">
                Preview Player
              </div>
            </div>

            {/* Video File Meta Card */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3 flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2.5 overflow-hidden">
                <FileVideo className="w-5 h-5 text-indigo-400 shrink-0" />
                <div className="overflow-hidden">
                  <p className="font-medium text-slate-200 truncate max-w-[220px]" title={video.filename}>
                    {video.filename}
                  </p>
                  <p className="text-[11px] text-slate-500 font-mono">
                    {formatBytes(video.size)}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => fileInputRef.current?.click()}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 transition-colors"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Đổi video</span>
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleRemove}
                  className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-colors"
                  title="Gỡ video này"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </motion.button>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 relative overflow-hidden ${
              isDragging
                ? 'border-indigo-400 bg-indigo-500/10 scale-[1.01] shadow-lg shadow-indigo-500/20'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/40 hover:bg-slate-950/60'
            }`}
          >
            {/* Animated Drag Aura */}
            {isDragging && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 animate-pulse pointer-events-none"
              />
            )}

            <div className="flex flex-col items-center justify-center space-y-3 relative z-10">
              <motion.div
                animate={isDragging ? { y: -6 } : { y: 0 }}
                transition={{ type: 'spring', stiffness: 300 }}
                className={`w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg transition-colors ${
                  isDragging
                    ? 'bg-indigo-500 text-white shadow-indigo-500/40'
                    : 'bg-slate-800/80 text-indigo-400 border border-slate-700/60'
                }`}
              >
                {uploading ? (
                  <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
                ) : (
                  <Upload className="w-6 h-6" />
                )}
              </motion.div>

              <div>
                <p className="text-sm font-semibold text-slate-200">
                  {uploading
                    ? 'Đang tải video lên server...'
                    : 'Kéo thả file video vào đây hoặc nhấp để duyệt'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Hỗ trợ định dạng <span className="text-indigo-300 font-mono">.MP4</span> hoặc{' '}
                  <span className="text-indigo-300 font-mono">.MOV</span> (tối đa 500MB)
                </p>
              </div>

              {/* Tag tips */}
              <div className="pt-2 flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-md bg-slate-800/60 text-[10px] text-slate-400 border border-slate-700/50">
                  TikTok 9:16
                </span>
                <span className="px-2 py-0.5 rounded-md bg-slate-800/60 text-[10px] text-slate-400 border border-slate-700/50">
                  Reels
                </span>
                <span className="px-2 py-0.5 rounded-md bg-slate-800/60 text-[10px] text-slate-400 border border-slate-700/50">
                  Shorts
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept="video/mp4,video/quicktime"
        className="hidden"
      />
    </motion.div>
  );
}
