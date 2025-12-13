/**
 * WebSocket client hook for real-time updates
 */
import { useEffect, useRef, useState, useCallback } from "react";
import type { WSLogMessage } from "@/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

interface UseWebSocketOptions {
  onLog?: (message: WSLogMessage) => void;
  onProgress?: (message: WSLogMessage) => void;
  onCheckpoint?: (message: WSLogMessage) => void;
  onComplete?: (message: WSLogMessage) => void;
  onError?: (message: WSLogMessage) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

export function useWebSocket(threadId: string | null, options: UseWebSocketOptions = {}) {
  const {
    onLog,
    onProgress,
    onCheckpoint,
    onComplete,
    onError,
    reconnectAttempts = 3,
    reconnectDelay = 1000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!threadId) return;

    try {
      const ws = new WebSocket(`${WS_URL}/ws/${threadId}`);

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
        setConnectionError(null);
        reconnectCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WSLogMessage = JSON.parse(event.data);

          switch (message.type) {
            case "log":
              onLog?.(message);
              break;
            case "progress":
              onProgress?.(message);
              break;
            case "checkpoint":
              onCheckpoint?.(message);
              break;
            case "complete":
              onComplete?.(message);
              break;
            case "error":
              onError?.(message);
              break;
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionError("Connection error");
      };

      ws.onclose = () => {
        console.log("WebSocket closed");
        setIsConnected(false);

        // Attempt reconnection with exponential backoff
        if (reconnectCountRef.current < reconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectCountRef.current);
          reconnectCountRef.current += 1;

          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectCountRef.current}/${reconnectAttempts})...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setConnectionError("Connection lost. Please refresh the page.");
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      setConnectionError("Failed to connect");
    }
  }, [threadId, onLog, onProgress, onCheckpoint, onComplete, onError, reconnectAttempts, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    connectionError,
    sendMessage,
    disconnect,
    reconnect: connect,
  };
}

