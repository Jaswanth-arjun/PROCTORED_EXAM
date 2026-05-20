/**
 * WebSocket hook — manages realtime connection to the backend.
 * Handles auto-reconnect, status tracking, and message dispatch.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = 'wss://proctored-exam-m0km.onrender.com/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT = 10;

export function useWebSocket(onResult, onStatusChange) {
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState('disconnected');
  const wsRef = useRef(null);
  const reconnectCount = useRef(0);
  const reconnectTimer = useRef(null);

  const updateStatus = useCallback((newStatus, detail = '') => {
    setStatus(newStatus);
    if (onStatusChange) onStatusChange(newStatus, detail);
  }, [onStatusChange]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectCount.current = 0;
        updateStatus('ready', 'Connected to server');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          switch (message.type) {
            case 'analysis_result':
              if (onResult) onResult(message.data);
              break;
            case 'status':
              updateStatus(
                message.data.status || 'ready',
                message.data.detail || ''
              );
              break;
            case 'error':
              updateStatus('error', message.data.message || 'Unknown error');
              break;
            case 'pong':
              break;
            default:
              console.warn('Unknown WS message type:', message.type);
          }
        } catch (err) {
          console.error('Failed to parse WS message:', err);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        updateStatus('disconnected', 'Connection lost');
        // Auto-reconnect
        if (reconnectCount.current < MAX_RECONNECT) {
          reconnectCount.current++;
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        updateStatus('error', 'Connection error');
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      updateStatus('error', 'Failed to connect');
    }
  }, [onResult, updateStatus]);

  // Send a capture frame
  const sendCapture = useCallback((imageBase64) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected');
      return false;
    }
    wsRef.current.send(JSON.stringify({
      type: 'capture',
      data: { image_base64: imageBase64 },
    }));
    return true;
  }, []);

  // Ping to keep alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
    return () => clearInterval(pingInterval);
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { connected, status, sendCapture, reconnect: connect };
}
