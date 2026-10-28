import React, { useState } from 'react';
import { Send, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
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
  };

  const enabledCount = Object.values(platformsConfig).filter((c) => c.enabled).length;

  const handlePublish = async () => {
    if (!video || !video.path) {
      setPublishMessage({
        type: 'error',
        text: 'Vui lòng tải video lên trước khi xuất bản!',
      });
      return;
    }

    if (enabledCount === 0) {
      setPublishMessage({
        type: 'error',
        text: 'Vui lòng chọn ít nhất 1 nền tảng để đăng video!',
      });
      return;
    }

    setPublishing(true);
    setPublishMessage(null);

    try {
      // Build publish payload
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
        text: `Đã bắt đầu tiến trình đăng video lên ${enabledCount} nền tảng! Theo dõi nhật ký bên dưới.`,
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <AccountStatusHeader />

      {/* Main Studio Split-Screen Layout */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 pb-28">
        {publishMessage && (
          <div
            className={`mb-6 p-4 rounded-xl border flex items-center justify-between gap-3 text-sm transition-all ${
              publishMessage.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}
          >
            <div className="flex items-center gap-2">
              {publishMessage.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
              )}
              <span>{publishMessage.text}</span>
            </div>
            <button
              onClick={() => setPublishMessage(null)}
              className="text-xs hover:underline opacity-80"
            >
              Đóng
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (40% width): Video Upload + AI Generator */}
          <div className="lg:col-span-5 space-y-6">
            <VideoUploadSection video={video} onVideoChange={setVideo} />
            <AIPromptSection onGenerated={handleAIGenerated} />
          </div>

          {/* Right Column (60% width): Platform Cards */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-base font-semibold text-white">
                Cấu Hình Nội Dung Đăng Tải
              </h2>
              <span className="text-xs text-slate-400">
                Đã kích hoạt:{' '}
                <strong className="text-indigo-400 font-mono">{enabledCount} / 4</strong> nền tảng
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {PLATFORMS_META.map((plat) => (
                <PlatformCard
                  key={plat.id}
                  platform={plat}
                  config={platformsConfig[plat.id]}
                  onChange={(newConf) => handlePlatformChange(plat.id, newConf)}
                />
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Sticky Bottom Action Bar */}
      <div className="fixed bottom-10 left-0 right-0 z-40 bg-slate-900/90 backdrop-blur-md border-t border-slate-800 px-6 py-3">
        <div className="max-w-[1600px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${video ? 'bg-emerald-400' : 'bg-amber-400'}`}
            />
            {video
              ? `Video sẵn sàng: ${video.filename}`
              : 'Chưa chọn video tải lên'}
          </div>

          <button
            onClick={handlePublish}
            disabled={publishing || !video || enabledCount === 0}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-600 hover:from-indigo-600 hover:via-purple-700 hover:to-pink-700 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {publishing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Đang gửi tiến trình đăng...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>🚀 Đăng Lên Tất Cả Nền Tảng Đã Chọn ({enabledCount})</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Real-time WebSocket Logs Drawer */}
      <LiveLogsDrawer />
    </div>
  );
}
