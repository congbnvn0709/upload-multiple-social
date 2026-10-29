import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, ExternalLink, CheckCircle2, AlertCircle, Sparkles, ShieldCheck, ShieldAlert } from 'lucide-react';

export const PLATFORMS_META = [
  { 
    id: 'tiktok', 
    name: 'TikTok', 
    badgeColor: 'border-cyan-500/30 text-cyan-400 bg-cyan-950/30',
    glowColor: 'shadow-cyan-500/20',
    activeGradient: 'from-cyan-500 to-pink-500',
    dotColor: 'bg-cyan-400'
  },
  { 
    id: 'threads', 
    name: 'Threads', 
    badgeColor: 'border-purple-500/30 text-purple-300 bg-purple-950/30',
    glowColor: 'shadow-purple-500/20',
    activeGradient: 'from-purple-500 to-indigo-500',
    dotColor: 'bg-purple-400'
  },
  { 
    id: 'facebook', 
    name: 'Facebook', 
    badgeColor: 'border-blue-500/30 text-blue-400 bg-blue-950/30',
    glowColor: 'shadow-blue-500/20',
    activeGradient: 'from-blue-600 to-cyan-600',
    dotColor: 'bg-blue-400'
  },
  { 
    id: 'youtube', 
    name: 'YouTube', 
    badgeColor: 'border-red-500/30 text-red-400 bg-red-950/30',
    glowColor: 'shadow-red-500/20',
    activeGradient: 'from-red-600 to-amber-600',
    dotColor: 'bg-red-400'
  },
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
        setTimeout(fetchStatus, 3000);
      }
    } catch (err) {
      console.error(`Failed to open login for ${platformId}:`, err);
    } finally {
      setOpeningPlatform(null);
    }
  };

  const connectedCount = Object.values(statuses).filter(Boolean).length;

  return (
    <header className="sticky top-0 z-30 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/80 px-4 sm:px-6 py-3.5 shadow-sm">
      <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Logo and Brand */}
        <div className="flex items-center space-x-3.5">
          <motion.div 
            whileHover={{ scale: 1.05, rotate: 5 }}
            whileTap={{ scale: 0.95 }}
            className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-500 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 font-bold text-white text-base cursor-pointer"
          >
            ▶
          </motion.div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-tight">
                Social Video Publisher
              </h1>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-indigo-400" />
                AI Studio
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Xuất bản video đa nền tảng một chạm với Playwright Browser & Gemini AI
            </p>
          </div>
        </div>

        {/* Account Badges and Connection Health */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Refresh Button */}
          <motion.button
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            onClick={fetchStatus}
            disabled={loading}
            title="Làm mới trạng thái tài khoản"
            className="p-2 text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-xl transition-all shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </motion.button>

          {/* Account Status Chips */}
          {PLATFORMS_META.map((plat) => {
            const isConnected = Boolean(statuses[plat.id]);
            const isOpening = openingPlatform === plat.id;

            return (
              <motion.div
                key={plat.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ y: -1 }}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-medium backdrop-blur-md transition-all shadow-sm ${
                  isConnected
                    ? `${plat.badgeColor} border-opacity-60 shadow-md ${plat.glowColor}`
                    : 'bg-slate-950/60 border-slate-800 text-slate-400'
                }`}
              >
                {/* Status Dot */}
                <span className="relative flex h-2 w-2">
                  {isConnected && (
                    <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${plat.dotColor} opacity-75`} />
                  )}
                  <span
                    className={`relative inline-flex rounded-full h-2 w-2 ${
                      isConnected ? plat.dotColor : 'bg-slate-600'
                    }`}
                  />
                </span>

                <span className="font-semibold text-slate-200">{plat.name}</span>

                {isConnected ? (
                  <span className="text-[10px] text-emerald-400 font-mono font-normal">
                    Đã lưu
                  </span>
                ) : (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleOpenLogin(plat.id)}
                    disabled={isOpening}
                    className="text-[10px] font-semibold text-indigo-400 hover:text-indigo-300 hover:underline flex items-center gap-0.5 ml-0.5"
                  >
                    <span>{isOpening ? 'Đang mở...' : 'Đăng nhập'}</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </motion.button>
                )}
              </motion.div>
            );
          })}
        </div>
      </div>
    </header>
  );
}
