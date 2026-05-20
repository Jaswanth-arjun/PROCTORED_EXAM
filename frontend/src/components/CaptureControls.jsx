/**
 * CaptureControls — Screen capture, file upload, and clipboard paste.
 */
import { useState, useRef, useCallback } from 'react';

export default function CaptureControls({ onCapture, status, connected }) {
  const [isCapturing, setIsCapturing] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [autoMode, setAutoMode] = useState(false);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  const blobToBase64 = (blob) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

  const captureFrame = useCallback(async (stream) => {
    const track = stream.getVideoTracks()[0];
    if (!track || track.readyState !== 'live') return null;
    const imageCapture = new ImageCapture(track);
    try {
      const bitmap = await imageCapture.grabFrame();
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      canvas.getContext('2d').drawImage(bitmap, 0, 0);
      const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
      return await blobToBase64(blob);
    } catch { return null; }
  }, []);

  const startCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: { cursor: 'never' }, audio: false });
      streamRef.current = stream;
      setIsCapturing(true);
      const b64 = await captureFrame(stream);
      if (b64) onCapture(b64);
      stream.getVideoTracks()[0].onended = () => stopCapture();
    } catch (err) { console.error('Screen capture failed:', err); }
  };

  const stopCapture = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null; }
    setIsCapturing(false);
    setAutoMode(false);
  };

  const recapture = async () => {
    if (!streamRef.current) return;
    const b64 = await captureFrame(streamRef.current);
    if (b64) onCapture(b64);
  };

  const toggleAutoMode = () => {
    if (autoMode) { clearInterval(intervalRef.current); intervalRef.current = null; setAutoMode(false); }
    else {
      intervalRef.current = setInterval(async () => {
        if (streamRef.current) { const b64 = await captureFrame(streamRef.current); if (b64) onCapture(b64); }
      }, 5000);
      setAutoMode(true);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file || !file.type.startsWith('image/')) return;
    onCapture(await blobToBase64(file));
  };

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer?.files?.[0]; if (f) handleFileUpload(f); };

  const handlePaste = async () => {
    try {
      const items = await navigator.clipboard.read();
      for (const item of items) {
        const t = item.types.find(t => t.startsWith('image/'));
        if (t) { onCapture(await blobToBase64(await item.getType(t))); return; }
      }
    } catch (err) { console.error('Paste failed:', err); }
  };

  const isProcessing = status === 'processing' || status === 'analyzing';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`status-dot ${connected ? status : 'disconnected'}`} />
          <span className="text-xs font-medium text-surface-400 uppercase tracking-wider">
            {connected ? status : 'Disconnected'}
          </span>
        </div>
        {isCapturing && (
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs text-red-400 font-medium">LIVE</span>
          </div>
        )}
      </div>

      {!isCapturing ? (
        <div
          className={`drop-zone flex flex-col items-center justify-center text-center min-h-[160px] ${dragOver ? 'active' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="w-12 h-12 rounded-2xl bg-accent/10 flex items-center justify-center mb-3">
            <svg className="w-6 h-6 text-accent-light" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-sm text-surface-300 font-medium mb-1">Drop an image or click to upload</p>
          <p className="text-xs text-surface-500">PNG, JPG, WEBP up to 10MB</p>
          <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => handleFileUpload(e.target.files?.[0])} />
        </div>
      ) : (
        <div className="glass-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-surface-200">Screen Capture Active</span>
            {autoMode && <span className="text-xs px-2 py-0.5 rounded-full bg-accent/20 text-accent-light font-medium">AUTO · 5s</span>}
          </div>
          <div className="flex gap-2">
            <button onClick={recapture} disabled={isProcessing} className="btn-primary flex-1 text-sm disabled:opacity-50">
              {isProcessing ? 'Processing...' : 'Capture Now'}
            </button>
            <button onClick={toggleAutoMode} className={`btn-ghost text-sm border ${autoMode ? 'border-accent/40 text-accent-light bg-accent/10' : 'border-surface-700/40'}`}>
              {autoMode ? 'Stop Auto' : 'Auto'}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <button onClick={isCapturing ? stopCapture : startCapture}
          className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all duration-200 ${isCapturing ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-surface-800/40 border-surface-700/30 text-surface-300 hover:border-accent/30 hover:text-accent-light'}`}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <span className="text-[10px] font-medium uppercase tracking-wider">{isCapturing ? 'Stop' : 'Screen'}</span>
        </button>
        <button onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center gap-1.5 p-3 rounded-xl border bg-surface-800/40 border-surface-700/30 text-surface-300 hover:border-accent/30 hover:text-accent-light transition-all">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <span className="text-[10px] font-medium uppercase tracking-wider">Upload</span>
        </button>
        <button onClick={handlePaste}
          className="flex flex-col items-center gap-1.5 p-3 rounded-xl border bg-surface-800/40 border-surface-700/30 text-surface-300 hover:border-accent/30 hover:text-accent-light transition-all">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <span className="text-[10px] font-medium uppercase tracking-wider">Paste</span>
        </button>
      </div>
    </div>
  );
}
