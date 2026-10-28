import React, { useState, useRef } from 'react';
import { Upload, Film, Trash2, CheckCircle2, AlertCircle } from 'lucide-react';

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

    // Client-side extension validation
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (ext !== '.mp4' && ext !== '.mov') {
      setError('Chỉ hỗ trợ tệp định dạng .mp4 hoặc .mov');
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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Film className="w-5 h-5 text-indigo-400" />
          Tải Video Lên
        </h2>
        {video && (
          <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Đã sẵn sàng
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!video ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-indigo-500 bg-indigo-500/5'
              : 'border-slate-700/80 hover:border-slate-600 bg-slate-950/40'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.mov,video/mp4,video/quicktime"
            onChange={handleFileSelect}
            className="hidden"
          />
          <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center mb-3 text-indigo-400">
            <Upload className={`w-7 h-7 ${uploading ? 'animate-bounce' : ''}`} />
          </div>
          <p className="text-sm font-medium text-slate-200">
            {uploading ? 'Đang tải video lên...' : 'Kéo thả video vào đây, hoặc bấm để chọn tệp'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Định dạng hỗ trợ: MP4, MOV (Tỉ lệ 9:16 tối ưu cho Reels/Shorts/TikTok)
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="aspect-[9/16] max-h-[360px] w-full bg-black rounded-lg overflow-hidden flex items-center justify-center border border-slate-800">
            <video
              src={video.stream_url}
              controls
              className="w-full h-full object-contain"
            />
          </div>

          <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-3 flex items-center justify-between">
            <div className="min-w-0 pr-3">
              <p className="text-xs font-semibold text-slate-200 truncate" title={video.filename}>
                {video.filename}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                {formatBytes(video.size)}
              </p>
            </div>
            <button
              onClick={handleRemove}
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors shrink-0"
              title="Xóa video và chọn lại"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
