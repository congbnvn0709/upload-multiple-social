import React, { useState, useEffect, useRef } from 'react';
import { Terminal, ChevronUp, ChevronDown, Trash2, CheckCircle2, AlertTriangle, Info, XCircle } from 'lucide-react';

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
          // Try reconnecting after 5 seconds
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
          <span className="flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 font-mono">
            <CheckCircle2 className="w-3 h-3" />
            SUCCESS
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1 text-[11px] text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20 font-mono">
            <XCircle className="w-3 h-3" />
            ERROR
          </span>
        );
      case 'warning':
        return (
          <span className="flex items-center gap-1 text-[11px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20 font-mono">
            <AlertTriangle className="w-3 h-3" />
            WARN
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20 font-mono">
            <Info className="w-3 h-3" />
            INFO
          </span>
        );
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 border-t border-slate-800 shadow-2xl">
      {/* Drawer Toggle Header */}
      <div className="px-6 py-2.5 bg-slate-950 flex items-center justify-between border-b border-slate-800/80">
        <div
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-3 cursor-pointer select-none"
        >
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
            <Terminal className="w-4 h-4 text-indigo-400" />
            <span>Nhật Ký Trực Tiếp (Live Logs)</span>
          </div>

          <span className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
            <span
              className={`w-2 h-2 rounded-full ${
                connected ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'
              }`}
            />
            {connected ? 'Trực tiếp' : 'Mất kết nối'}
          </span>

          {logs.length > 0 && (
            <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-mono">
              {logs.length} sự kiện
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {logs.length > 0 && (
            <button
              onClick={clearLogs}
              title="Xóa logs"
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
            title={isOpen ? 'Thu nhỏ' : 'Mở rộng'}
          >
            {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Drawer Content */}
      {isOpen && (
        <div
          ref={logContainerRef}
          className="h-56 overflow-y-auto p-4 font-mono text-xs space-y-2 bg-slate-950/95"
        >
          {logs.length === 0 ? (
            <p className="text-slate-500 italic">Chưa có nhật ký nào từ phiên đăng video...</p>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                className="flex items-start gap-3 py-1 border-b border-slate-900/60 last:border-0 hover:bg-slate-900/40 px-2 rounded"
              >
                <span className="text-[11px] text-slate-500 whitespace-nowrap">
                  {log.timestamp}
                </span>

                <div className="shrink-0">{getStatusBadge(log.status)}</div>

                <span className="text-indigo-400 uppercase text-[11px] font-semibold whitespace-nowrap">
                  [{log.platform}]
                </span>

                <span className="text-slate-200 break-words">{log.message}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
