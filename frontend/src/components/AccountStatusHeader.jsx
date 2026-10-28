import React, { useEffect, useState } from 'react';
import { RefreshCw, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react';

export const PLATFORMS_META = [
  { id: 'tiktok', name: 'TikTok', color: 'from-pink-500 to-rose-500' },
  { id: 'threads', name: 'Threads', color: 'from-purple-500 to-indigo-500' },
  { id: 'facebook', name: 'Facebook', color: 'from-blue-600 to-blue-500' },
  { id: 'youtube', name: 'YouTube', color: 'from-red-600 to-red-500' },
];

export default function AccountStatusHeader({ onStatusChange }) {
  const [statuses, setStatuses] = useState({
    tiktok: false,
    threads: false,
    facebook: false,
    youtube: false,
  });
  const [loading, setLoading] = useState(false);
  const [openingPlatform, setOpeningPlatform] = useState(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/accounts/status');
      if (res.ok) {
        const data = await res.json();
        // data can be { tiktok: true, ... } or { tiktok: { logged_in: true }, ... }
        const parsed = {};
        for (const [key, val] of Object.entries(data)) {
          parsed[key] = typeof val === 'object' && val !== null ? Boolean(val.logged_in) : Boolean(val);
        }
        setStatuses((prev) => ({ ...prev, ...parsed }));
        if (onStatusChange) onStatusChange(parsed);
      }
    } catch (err) {
      console.error('Failed to fetch account status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenLogin = async (platformId) => {
    setOpeningPlatform(platformId);
    try {
      const res = await fetch('/api/accounts/open-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform: platformId }),
      });
      if (res.ok) {
        // Poll status after opening
        setTimeout(fetchStatus, 3000);
      }
    } catch (err) {
      console.error(`Failed to open login for ${platformId}:`, err);
    } finally {
      setOpeningPlatform(null);
    }
  };

  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 font-bold text-white text-lg">
          ▶
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Social Video Publisher
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Studio
            </span>
          </h1>
          <p className="text-xs text-slate-400">
            Xuất bản video tự động đa nền tảng với Playwright & AI
          </p>
        </div>
      </div>

      {/* Account Badges */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={fetchStatus}
          disabled={loading}
          title="Làm mới trạng thái tài khoản"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors mr-1"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
        </button>

        {PLATFORMS_META.map((plat) => {
          const isConnected = Boolean(statuses[plat.id]);
          const isOpening = openingPlatform === plat.id;

          return (
            <div
              key={plat.id}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                isConnected
                  ? 'bg-slate-800/80 border-slate-700 text-slate-200'
                  : 'bg-slate-900/60 border-slate-800/80 text-slate-400'
              }`}
            >
              <span className="flex items-center gap-1.5 font-semibold">
                {isConnected ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-3.5 h-3.5 text-amber-500/80" />
                )}
                {plat.name}
              </span>

              {isConnected ? (
                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded font-mono">
                  Đã kết nối
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => handleOpenLogin(plat.id)}
                  disabled={isOpening}
                  className="flex items-center gap-1 text-[11px] bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-0.5 rounded transition-colors disabled:opacity-50"
                >
                  <ExternalLink className="w-2.5 h-2.5" />
                  {isOpening ? 'Đang mở...' : 'Đăng nhập'}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </header>
  );
}
