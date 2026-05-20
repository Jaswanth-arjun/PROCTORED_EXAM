import React, { useState, useEffect, useRef, useCallback } from 'react';
import AnswerCard from './components/AnswerCard';
import HistoryPanel from './components/HistoryPanel';
import Dashboard from './components/Dashboard';
import { useWebSocket } from './hooks/useWebSocket';
import { fetchHistory, fetchStats, analyzeImage } from './services/api';

export default function App() {
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedResult, setSelectedResult] = useState(null);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [statusDetail, setStatusDetail] = useState('');
  const [activeTab, setActiveTab] = useState('solve');
  const [isScanning, setIsScanning] = useState(false);
  const [autoScan, setAutoScan] = useState(false);
  const [scanCount, setScanCount] = useState(0);
  const [lastScanTime, setLastScanTime] = useState(null);
  const [isCompact, setIsCompact] = useState(false);

  const isElectron = typeof window !== 'undefined' && !!window.electron;
  const [isAlwaysOnTop, setIsAlwaysOnTop] = useState(true);
  const autoScanRef = useRef(null);
  const scanCountRef = useRef(0);

  useEffect(() => {
    if (isElectron) {
      window.electron.onAlwaysOnTopStatus((flag) => setIsAlwaysOnTop(flag));
      window.electron.onTriggerCapture(() => handleScanScreen());
    }
  }, [isElectron]);

  // Load initial data
  const loadData = async () => {
    try {
      const histData = await fetchHistory();
      setHistory(histData.items || []);
      const statsData = await fetchStats();
      setStats(statsData);
      if (histData.items?.length > 0 && !selectedResult) {
        setSelectedResult(histData.items[0]);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  useEffect(() => { loadData(); }, []);

  // WebSocket handlers
  const handleWebSocketResult = useCallback((result) => {
    setSelectedResult(result);
    setHistory((prev) => [result, ...prev]);
    scanCountRef.current++;
    setScanCount(scanCountRef.current);
    setLastScanTime(new Date());
    fetchStats().then(setStats).catch(console.error);
  }, []);

  const handleWebSocketStatus = useCallback((status, detail) => {
    setWsStatus(status);
    setStatusDetail(detail);
    if (status === 'ready' || status === 'error') {
      setIsScanning(false);
    }
  }, []);

  const { connected, sendCapture } = useWebSocket(
    handleWebSocketResult,
    handleWebSocketStatus
  );

  // ─── Core: Capture screen and send for analysis ─────────────
  const handleScanScreen = useCallback(async () => {
    if (isScanning) return;
    setIsScanning(true);
    setStatusDetail('Capturing screen...');
    setWsStatus('processing');

    try {
      if (isElectron && window.electron.captureScreen) {
        // Native Electron capture (silent, no dialog)
        const capture = await window.electron.captureScreen();
        if (!capture.success) {
          throw new Error(capture.error || 'Screen capture failed');
        }

        const sent = sendCapture(capture.image_base64);
        if (!sent) {
          // Fallback to REST
          setStatusDetail('Analyzing via REST...');
          const result = await analyzeImage(capture.image_base64, 'screen_capture');
          handleWebSocketResult(result);
          setWsStatus('ready');
          setStatusDetail(`Completed in ${result.processing_time_ms}ms`);
        }
      } else {
        // Browser fallback: use getDisplayMedia
        try {
          const stream = await navigator.mediaDevices.getDisplayMedia({
            video: { cursor: 'never' },
            audio: false,
          });
          const track = stream.getVideoTracks()[0];
          const imageCapture = new ImageCapture(track);
          const bitmap = await imageCapture.grabFrame();
          const canvas = document.createElement('canvas');
          canvas.width = bitmap.width;
          canvas.height = bitmap.height;
          canvas.getContext('2d').drawImage(bitmap, 0, 0);
          const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
          const reader = new FileReader();
          const b64 = await new Promise((resolve, reject) => {
            reader.onloadend = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
          });
          stream.getTracks().forEach(t => t.stop());

          const sent = sendCapture(b64);
          if (!sent) {
            const result = await analyzeImage(b64, 'screen_capture');
            handleWebSocketResult(result);
            setWsStatus('ready');
          }
        } catch (err) {
          throw new Error('Screen capture not available in browser mode');
        }
      }
    } catch (err) {
      console.error('Scan failed:', err);
      setWsStatus('error');
      setStatusDetail(err.message || 'Scan failed');
      setIsScanning(false);
    }
  }, [isScanning, isElectron, sendCapture]);

  // ─── Auto-scan toggle ──────────────────────────────────────
  const toggleAutoScan = useCallback(() => {
    if (autoScan) {
      clearInterval(autoScanRef.current);
      autoScanRef.current = null;
      setAutoScan(false);
    } else {
      // Immediate first scan
      handleScanScreen();
      autoScanRef.current = setInterval(() => {
        handleScanScreen();
      }, 8000);
      setAutoScan(true);
    }
  }, [autoScan, handleScanScreen]);

  // Cleanup auto-scan on unmount
  useEffect(() => {
    return () => {
      if (autoScanRef.current) clearInterval(autoScanRef.current);
    };
  }, []);

  // Toggle compact mode
  const toggleCompact = () => {
    const next = !isCompact;
    setIsCompact(next);
    if (isElectron) {
      window.electron.resize(next ? 'compact' : 'expanded');
    }
  };

  const isProcessing = isScanning || wsStatus === 'processing' || wsStatus === 'analyzing';

  return (
    <div className="glass-overlay min-h-screen flex flex-col p-4 overflow-hidden">
      {/* ─── Titlebar (Draggable) ─────────────────────────────── */}
      <div
        className="flex items-center justify-between pb-2 mb-2 border-b border-white/5 select-none"
        style={{ WebkitAppRegion: 'drag' }}
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-500 via-purple-500 to-cyan-400 flex items-center justify-center shadow-lg">
              <span className="text-sm">🧠</span>
            </div>
            {isProcessing && (
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse border border-black/30" />
            )}
          </div>
          <div>
            <h1 className="text-xs font-extrabold tracking-tight text-white/90">ATLAS</h1>
            <p className="text-[8px] font-semibold text-indigo-300/70 uppercase tracking-widest">
              {autoScan ? 'AUTO-SCANNING' : 'MCQ SOLVER'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-0.5" style={{ WebkitAppRegion: 'no-drag' }}>
          {/* Compact toggle */}
          <button
            onClick={toggleCompact}
            className="p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/5 transition-colors"
            title={isCompact ? 'Expand' : 'Compact'}
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isCompact ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.5 3.5M9 15v4.5M9 15H4.5M9 15l-5.5 5.5M15 9h4.5M15 9V4.5M15 9l5.5-5.5M15 15h4.5M15 15v4.5m0-4.5l5.5 5.5" />
              )}
            </svg>
          </button>
          {/* Pin */}
          {isElectron && (
            <button
              onClick={() => {
                const next = !isAlwaysOnTop;
                window.electron.setAlwaysOnTop(next);
                setIsAlwaysOnTop(next);
              }}
              className={`p-1.5 rounded-lg transition-colors ${isAlwaysOnTop ? 'text-indigo-400' : 'text-white/30 hover:text-white/70'} hover:bg-white/5`}
              title={isAlwaysOnTop ? 'Unpin' : 'Pin on top'}
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a1 1 0 011 1v1.323l3.945 1.183a1 1 0 01.69 1.226l-1.5 5a1 1 0 01-1.226.69L11 11.237V17a1 1 0 11-2 0v-5.763L5.09 10.038a1 1 0 01-1.226-.69l-1.5-5a1 1 0 01.69-1.226L7 4.323V3a1 1 0 011-1h2z" />
              </svg>
            </button>
          )}
          {/* Minimize */}
          {isElectron && (
            <button
              onClick={() => window.electron.minimize()}
              className="p-1.5 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/5 transition-colors"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
              </svg>
            </button>
          )}
          {/* Close */}
          {isElectron && (
            <button
              onClick={() => window.electron.close()}
              className="p-1.5 rounded-lg text-white/30 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* ─── Scan Controls ────────────────────────────────────── */}
      <div className="mb-3 space-y-2">
        {/* Main scan button */}
        <div className="flex gap-2">
          <button
            onClick={handleScanScreen}
            disabled={isProcessing}
            className={`btn-scan flex-1 flex items-center justify-center gap-2 text-sm ${isProcessing ? 'scanning opacity-80' : ''}`}
          >
            {isProcessing ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span>Scan Screen</span>
              </>
            )}
          </button>

          {/* Auto-scan toggle */}
          <button
            onClick={toggleAutoScan}
            className={`px-3 py-2.5 rounded-2xl font-semibold text-xs transition-all border ${
              autoScan
                ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300 shadow-[0_0_15px_rgba(99,102,241,0.2)]'
                : 'bg-white/3 border-white/8 text-white/50 hover:text-white/80 hover:border-white/15'
            }`}
            title={autoScan ? 'Stop auto-scan' : 'Auto-scan every 8s'}
          >
            {autoScan ? (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
          </button>
        </div>

        {/* Status bar */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-1.5">
            <div className={`status-dot ${connected ? (isProcessing ? 'scanning' : 'ready') : 'disconnected'}`} />
            <span className="text-[10px] text-white/40 font-medium">
              {statusDetail || (connected ? 'Ready' : 'Connecting...')}
            </span>
          </div>
          {scanCount > 0 && (
            <span className="text-[10px] text-white/25 font-mono">
              {scanCount} scan{scanCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* Hotkey hint */}
        {isElectron && !isCompact && (
          <div className="text-center">
            <span className="text-[9px] text-white/20 font-medium">
              Hotkey: <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/8 text-white/35 font-mono text-[8px]">Ctrl+Shift+S</kbd>
            </span>
          </div>
        )}
      </div>

      {/* ─── Tab Switcher ─────────────────────────────────────── */}
      {!isCompact && (
        <div className="flex gap-1 p-1 rounded-xl bg-white/3 border border-white/5 mb-3">
          {[
            { key: 'solve', label: 'Answer', icon: '✦' },
            { key: 'history', label: 'History', icon: '◷' },
            { key: 'stats', label: 'Stats', icon: '◈' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 px-2 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all ${
                activeTab === tab.key
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 shadow-sm'
                  : 'text-white/30 hover:text-white/60'
              }`}
            >
              <span className="mr-1">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* ─── Content Area ─────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden pr-0.5 space-y-3">
        {/* Solve / Answer tab */}
        {activeTab === 'solve' && (
          <>
            {selectedResult ? (
              <AnswerCard result={selectedResult} isLatest={true} />
            ) : (
              <div className="glass-card p-6 text-center animate-fade-in">
                <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/10 flex items-center justify-center">
                  <svg className="w-7 h-7 text-indigo-400/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <p className="text-sm font-semibold text-white/40 mb-1">No results yet</p>
                <p className="text-[10px] text-white/20 leading-relaxed">
                  Click <strong className="text-indigo-400/60">Scan Screen</strong> to capture
                  and analyze the background
                </p>
              </div>
            )}
          </>
        )}

        {/* History tab */}
        {activeTab === 'history' && !isCompact && (
          <div className="glass-card p-3 space-y-3 animate-fade-in">
            <h2 className="text-xs font-bold text-white/50 uppercase tracking-wider">Recent Scans</h2>
            <HistoryPanel
              history={history}
              activeId={selectedResult?.id}
              onSelect={(item) => {
                setSelectedResult(item);
                setActiveTab('solve');
              }}
            />
          </div>
        )}

        {/* Stats tab */}
        {activeTab === 'stats' && !isCompact && (
          <div className="glass-card p-3 space-y-3 animate-fade-in">
            <h2 className="text-xs font-bold text-white/50 uppercase tracking-wider">Analytics</h2>
            <Dashboard stats={stats} />
          </div>
        )}
      </div>

      {/* ─── Footer ───────────────────────────────────────────── */}
      {!isCompact && (
        <div className="mt-2 pt-2 border-t border-white/3 text-center">
          <p className="text-[8px] text-white/15 font-medium tracking-wide">
            ATLAS MCQ ASSISTANT · FOR EDUCATIONAL USE ONLY
          </p>
        </div>
      )}
    </div>
  );
}
