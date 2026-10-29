import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, AlertCircle, CheckCircle2, Loader2, Sparkles, 
  CheckSquare, Square, Copy, RefreshCw, Zap, Video 
} from 'lucide-react';
import AccountStatusHeader, { PLATFORMS_META } from './components/AccountStatusHeader';
import VideoUploadSection from './components/VideoUploadSection';
import AIPromptSection from './components/AIPromptSection';
import PlatformCard from './components/PlatformCard';
import LiveLogsDrawer from './components/LiveLogsDrawer';

export default function App() {
  const [video, setVideo] = useState(null);
  const [platformsConfig, setPlatformsConfig] = useState({
    tiktok: {
      enabled: true,
      caption: '',
      hashtags: ['fyp', 'xuhuong'],
    },
    threads: {
      enabled: true,
      caption: '',
      hashtags: [],
    },
    facebook: {
      enabled: true,
      caption: '',
      hashtags: [],
      target: 'profile', // 'profile' or 'fanpage'
      page_id: '',
    },
    youtube: {
      enabled: true,
      title: '',
      caption: '',
      hashtags: ['Shorts'],
      tags: [],
      visibility: 'public', // 'public', 'unlisted', 'private'
    },
  });

  const [publishing, setPublishing] = useState(false);
  const [publishMessage, setPublishMessage] = useState(null);

  const handlePlatformChange = (platId, newConfig) => {
    setPlatformsConfig((prev) => ({
      ...prev,
      [platId]: newConfig,
    }));
  };

  const handleAIGenerated = (aiData) => {
    setPlatformsConfig((prev) => {
      const updated = { ...prev };

      if (aiData.tiktok) {
        updated.tiktok = {
          ...updated.tiktok,
          caption: aiData.tiktok.caption || '',
          hashtags: aiData.tiktok.hashtags || [],
        };
      }

      if (aiData.threads) {
        updated.threads = {
          ...updated.threads,
          caption: aiData.threads.caption || '',
          hashtags: aiData.threads.hashtags || [],
        };
      }

      if (aiData.facebook) {
        updated.facebook = {
          ...updated.facebook,
          caption: aiData.facebook.caption || '',
          hashtags: aiData.facebook.hashtags || [],
        };
      }

      if (aiData.youtube) {
        updated.youtube = {
          ...updated.youtube,
          title: aiData.youtube.title || '',
          caption: aiData.youtube.description || '',
          hashtags: aiData.youtube.tags || [],
        };
      }

      return updated;
    });

    setPublishMessage({
      type: 'success',
      text: '✨ Đã điền xong nội dung AI cho 4 nền tảng! Bạn có thể tinh chỉnh trước khi đăng.',
    });
  };

  const enabledCount = Object.values(platformsConfig).filter((c) => c.enabled).length;

  // Bulk actions for usability
  const handleSelectAll = (select) => {
    setPlatformsConfig((prev) => {
      const next = {};
      for (const [key, val] of Object.entries(prev)) {
        next[key] = { ...val, enabled: select };
      }
      return next;
    });
  };

  const handleSyncCaptions = () => {
    // Find the first platform with a non-empty caption (priority: tiktok -> facebook -> threads -> youtube)
    const sourceCaption = 
      platformsConfig.tiktok.caption ||
      platformsConfig.facebook.caption ||
      platformsConfig.threads.caption ||
      platformsConfig.youtube.caption;

    if (!sourceCaption) {
      setPublishMessage({
        type: 'error',
        text: 'Chưa có caption nào để đồng bộ! Hãy nhập nội dung vào một nền tảng hoặc dùng AI.',
      });
      return;
    }

    setPlatformsConfig((prev) => {
      const next = { ...prev };
      for (const key of Object.keys(next)) {
        next[key] = {
          ...next[key],
          caption: sourceCaption,
        };
      }
      return next;
    });

    setPublishMessage({
      type: 'success',
      text: 'Đã sao chép nội dung đồng bộ cho tất cả nền tảng!',
    });
  };

  const handleClearAllCaptions = () => {
    setPlatformsConfig((prev) => {
      const next = {};
      for (const [key, val] of Object.entries(prev)) {
        next[key] = {
          ...val,
          caption: '',
          title: '',
        };
      }
      return next;
    });
  };

  const handlePublish = async () => {
    if (!video || !video.path) {
      setPublishMessage({
        type: 'error',
        text: 'Vui lòng kéo thả hoặc chọn video tải lên trước khi xuất bản!',
      });
      return;
    }

    if (enabledCount === 0) {
      setPublishMessage({
        type: 'error',
        text: 'Vui lòng chọn ít nhất 1 nền tảng mạng xã hội để đăng video!',
      });
      return;
    }

    setPublishing(true);
    setPublishMessage(null);

    try {
      const payloadPlatforms = {};
      for (const [key, conf] of Object.entries(platformsConfig)) {
        payloadPlatforms[key] = {
          enabled: conf.enabled,
          caption: conf.caption || '',
          hashtags: conf.hashtags || [],
          title: conf.title || '',
          description: conf.caption || '',
          tags: conf.hashtags || [],
          target: conf.target || 'profile',
          page_id: conf.page_id || '',
          visibility: conf.visibility || 'public',
        };
      }

      const res = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: video.path,
          platforms: payloadPlatforms,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Không thể bắt đầu tiến trình đăng video');
      }

      const data = await res.json();
      setPublishMessage({
        type: 'success',
        text: `🚀 Đã khởi động bot tự động đăng tải lên ${enabledCount} nền tảng! Xem nhật ký trực tiếp bên dưới.`,
      });
    } catch (err) {
      console.error('Publish error:', err);
      setPublishMessage({
        type: 'error',
        text: err.message || 'Lỗi khi gửi yêu cầu đăng video',
      });
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0D14] bg-ambient-glow text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30">
      {/* Top Header */}
      <AccountStatusHeader />

      {/* Main Studio Split-Screen Layout */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 pb-32">
        {/* Floating Notification */}
        <AnimatePresence>
          {publishMessage && (
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              className={`mb-6 p-4 rounded-2xl border flex items-center justify-between gap-3 text-sm shadow-xl backdrop-blur-xl ${
                publishMessage.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              }`}
            >
              <div className="flex items-center gap-2.5">
                {publishMessage.type === 'success' ? (
                  <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
                )}
                <span className="font-medium">{publishMessage.text}</span>
              </div>
              <button
                onClick={() => setPublishMessage(null)}
                className="text-xs hover:underline opacity-80 cursor-pointer px-2 py-1 rounded hover:bg-white/5"
              >
                Đóng
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (40% width): Video Upload + AI Generator */}
          <div className="lg:col-span-5 space-y-6">
            <VideoUploadSection video={video} onVideoChange={setVideo} />
            <AIPromptSection onGenerated={handleAIGenerated} />
          </div>

          {/* Right Column (60% width): Platform Cards */}
          <div className="lg:col-span-7 space-y-4">
            {/* Usability Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800/80">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white tracking-wide">
                  Cấu Hình 4 Nền Tảng
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold">
                  {enabledCount} / 4 hoạt động
                </span>
              </div>

              {/* Quick Actions */}
              <div className="flex items-center gap-1.5 text-xs">
                <button
                  type="button"
                  onClick={() => handleSelectAll(enabledCount < 4)}
                  className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/50 flex items-center gap-1 transition-all"
                  title="Bật hoặc tắt tất cả nền tảng"
                >
                  {enabledCount === 4 ? (
                    <>
                      <Square className="w-3.5 h-3.5" />
                      <span>Bỏ chọn</span>
                    </>
                  ) : (
                    <>
                      <CheckSquare className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Chọn hết</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={handleSyncCaptions}
                  className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/50 flex items-center gap-1 transition-all"
                  title="Sao chép nội dung sang tất cả nền tảng"
                >
                  <Copy className="w-3.5 h-3.5 text-purple-400" />
                  <span>Đồng bộ text</span>
                </button>

                <button
                  type="button"
                  onClick={handleClearAllCaptions}
                  className="px-2.5 py-1 rounded-lg bg-slate-800/70 hover:bg-rose-950/40 text-slate-400 hover:text-rose-300 border border-slate-700/50 transition-all"
                  title="Xóa nhanh nội dung"
                >
                  <span>Xóa hết</span>
                </button>
              </div>
            </div>

            {/* Platform Cards Grid with Framer Motion Stagger */}
            <motion.div 
              layout
              className="grid grid-cols-1 md:grid-cols-2 gap-4"
            >
              {PLATFORMS_META.map((plat) => (
                <PlatformCard
                  key={plat.id}
                  platform={plat}
                  config={platformsConfig[plat.id]}
                  onChange={(newConf) => handlePlatformChange(plat.id, newConf)}
                />
              ))}
            </motion.div>
          </div>
        </div>
      </main>

      {/* Floating Modern Action Dock */}
      <motion.div 
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 300 }}
        className="fixed bottom-10 left-0 right-0 z-40 px-4 sm:px-6 pointer-events-none"
      >
        <div className="max-w-[1600px] mx-auto flex justify-end pointer-events-auto">
          <div className="bg-slate-900/95 backdrop-blur-2xl border border-slate-700/70 rounded-2xl p-2.5 shadow-2xl flex flex-col sm:flex-row items-center gap-3">
            <div className="text-xs text-slate-300 px-3 flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${video ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}
              />
              <span className="max-w-[200px] truncate font-medium">
                {video ? video.filename : 'Chưa tải video lên'}
              </span>
            </div>

            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={handlePublish}
              disabled={publishing || !video || enabledCount === 0}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 hover:from-indigo-600 hover:via-purple-700 hover:to-pink-600 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all cursor-pointer"
            >
              {publishing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang gửi tiến trình đăng bài...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>🚀 Đăng Lên Tất Cả Nền Tảng Đã Chọn ({enabledCount})</span>
                </>
              )}
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Real-time WebSocket Logs Drawer */}
      <LiveLogsDrawer />
    </div>
  );
}
