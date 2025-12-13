"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef } from "react";
import { formatTime } from "@/lib/utils";
import type { WSLogMessage } from "@/types";

interface TerminalLogsProps {
  logs: WSLogMessage[];
  maxLogs?: number;
}

export default function TerminalLogs({ logs, maxLogs = 10 }: TerminalLogsProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const visibleLogs = logs.slice(-maxLogs);

  const getLogColor = (logType?: string) => {
    switch (logType) {
      case "success":
        return "text-green-500";
      case "error":
        return "text-red-500";
      case "info":
      default:
        return "text-gray-400";
    }
  };

  const getLogIcon = (logType?: string) => {
    switch (logType) {
      case "success":
        return "✓";
      case "error":
        return "✗";
      case "info":
      default:
        return "→";
    }
  };

  return (
    <div className="w-full h-64 bg-gray-900 rounded-lg overflow-hidden border border-gray-800">
      <div className="px-4 py-2 bg-gray-800 border-b border-gray-700 flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-red-500" />
        <div className="w-3 h-3 rounded-full bg-yellow-500" />
        <div className="w-3 h-3 rounded-full bg-green-500" />
        <span className="ml-2 text-sm text-gray-400 font-mono">Terminal</span>
      </div>

      <div
        ref={containerRef}
        className="h-[calc(100%-40px)] overflow-y-auto p-4 space-y-1 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900"
      >
        {visibleLogs.length === 0 ? (
          <div className="text-gray-500 font-mono text-sm">
            Waiting for analysis to start...
          </div>
        ) : (
          <AnimatePresence>
            {visibleLogs.map((log, index) => (
              <motion.div
                key={`${log.timestamp}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className={`font-mono text-sm ${getLogColor(log.data.log_type)}`}
              >
                <span className="text-gray-600">
                  {formatTime(log.timestamp)}
                </span>
                {" "}
                <span className="mr-2">
                  {getLogIcon(log.data.log_type)}
                </span>
                <span>{log.data.message}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

