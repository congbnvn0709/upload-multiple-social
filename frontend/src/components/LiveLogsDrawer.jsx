import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Terminal, ChevronUp, ChevronDown, Trash2, CheckCircle2, 
  AlertTriangle, Info, XCircle, Activity, Sparkles 
} from 'lucide-react';

export default function LiveLogsDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const logContainerRef = useRef(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

    let ws = null;
    let reconnectTimeout = null;

    const connectWs = () => {
      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setLogs((prev) => [
              ...prev,
              {
                id: Date.now() + Math.random(),
                timestamp: data.timestamp || new Date().toLocaleTimeString(),
                platform: data.platform || 'system',
                status: data.status || 'info',
                message: data.message || '',
              },
            ]);
            // Automatically open drawer on active publishing logs
            setIsOpen(true);
          } catch (e) {
            console.error('Failed to parse WebSocket log message:', e);
          }
        };

        ws.onclose = () => {
          setConnected(false);
          reconnectTimeout = setTimeout(connectWs, 5000);
        };

        ws.onerror = (err) => {
          console.error('WebSocket log error:', err);
          ws.close();
        };
      } catch (err) {
        console.error('WebSocket connection failed:', err);
      }
    };

    connectWs();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const clearLogs = () => {
    setLogs([]);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'success':
        return (
          <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 font-mono">
            <CheckCircle2 className="w-3 h-3" />
            SUCCESS
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1 text-[10px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20 font-mono">
            <XCircle className="w-3 h-3" />
            ERROR
          </span>
        );
      case 'warning':
        return (
          <span className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20 font-mono">
            <AlertTriangle className="w-3 h-3" />
            WARN
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[10px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20 font-mono">
            <Info className="w-3 h-3" />
            INFO
          </span>
        );
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 pointer-events-none">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 pointer-events-auto">
        <motion.div 
          layout
          className="bg-slate-900/95 backdrop-blur-2xl border-t border-x border-slate-800 rounded-t-2xl shadow-2xl overflow-hidden"
        >
          {/* Header Bar */}
          <div
            onClick={() => setIsOpen(!isOpen)}
            className="px-4 py-2.5 bg-slate-950/80 hover:bg-slate-950 flex items-center justify-between cursor-pointer border-b border-slate-800/80 transition-colors select-none"
          >
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-semibold text-slate-200">
                  Nhật Ký Trực Tiếp (Live Logs)
                </span>
              </div>

              {/* Live Connection Orb */}
              <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800">
                <span className="relative flex h-2 w-2">
                  {connected && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  )}
                  <span
                    className={`relative inline-flex rounded-full h-2 w-2 ${
                      connected ? 'bg-emerald-400' : 'bg-slate-600'
                    }`}
                  />
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {connected ? 'WebSocket kết nối' : 'Đang thử kết nối lại...'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {logs.length > 0 && (
                <span className="text-[11px] font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                  {logs.length} sự kiện
                </span>
              )}

              {isOpen && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    clearLogs();
                  }}
                  className="p-1 text-slate-400 hover:text-rose-400 rounded transition-colors text-xs flex items-center gap-1"
                  title="Xóa toàn bộ log"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span className="text-[11px]">Xóa</span>
                </button>
              )}

              <button className="text-slate-400 hover:text-white p-0.5">
                {isOpen ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronUp className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          {/* Collapsible Log Terminal Body */}
          <AnimatePresence>
            {isOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 240, opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                ref={logContainerRef}
                className="overflow-y-auto p-3.5 font-mono text-xs space-y-1.5 bg-slate-950/90"
              >
                {logs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-1 py-8">
                    <Activity className="w-6 h-6 text-slate-600 animate-pulse" />
                    <p className="text-xs">Chưa có sự kiện nào. Khi bạn bấm đăng, tiến trình tải video sẽ xuất hiện tại đây.</p>
                  </div>
                ) : (
                  logs.map((log) => (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-start gap-2.5 py-1 px-2 rounded-lg hover:bg-slate-900/60 transition-colors border-l-2 border-transparent hover:border-indigo-500"
                    >
                      <span className="text-slate-500 text-[10px] shrink-0 pt-0.5">
                        {log.timestamp}
                      </span>
                      {getStatusBadge(log.status)}
                      <span className="text-slate-400 uppercase text-[10px] bg-slate-800/80 px-1.5 py-0.5 rounded shrink-0">
                        {log.platform}
                      </span>
                      <span className="text-slate-200 text-xs flex-1 break-all">
                        {log.message}
                      </span>
                    </motion.div>
                  ))
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  );
}
