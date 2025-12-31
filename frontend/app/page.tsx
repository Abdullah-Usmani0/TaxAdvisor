"use client";

import { useState, useEffect, useRef } from "react";
import { Building2 } from "lucide-react";
import TranscriptInput from "@/components/TranscriptInput";
import TerminalLogs from "@/components/TerminalLogs";
import ProgressTracker from "@/components/ProgressTracker";
import CheckpointReview from "@/components/CheckpointReview";
import ReportViewer from "@/components/ReportViewer";
import { useWebSocket } from "@/lib/websocket";
import {
  getCheckpoint,
  approveCheckpoint,
} from "@/lib/api";
import type { WSLogMessage, CheckpointData } from "@/types";

type AppState = 'input' | 'processing' | 'checkpoint' | 'complete';

export default function Home() {
  // State management
  const [appState, setAppState] = useState<AppState>('input');
  const [threadId, setThreadId] = useState<string | null>(null);
  const [logs, setLogs] = useState<WSLogMessage[]>([]);
  const [currentStep, setCurrentStep] = useState('');
  const [progressPercentage, setProgressPercentage] = useState(0);
  const [checkpointData, setCheckpointData] = useState<CheckpointData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const completionRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to completion section when workflow completes
  useEffect(() => {
    if (appState === 'complete' && completionRef.current) {
      // Small delay to ensure DOM is updated
      setTimeout(() => {
        completionRef.current?.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        });
      }, 100);
    }
  }, [appState]);

  // WebSocket connection
  const { sendMessage, waitForConnection } = useWebSocket(threadId, {
    onLog: (message) => {
      setLogs((prev) => [...prev, message]);
    },
    onProgress: (message) => {
      if (message.data.current_step) {
        setCurrentStep(message.data.current_step);
      }
      if (message.data.progress_percentage !== undefined) {
        setProgressPercentage(message.data.progress_percentage);
      }
    },
    onCheckpoint: async () => {
      if (threadId) {
        try {
          const data = await getCheckpoint(threadId);
          setCheckpointData(data);
          setAppState('checkpoint');
          setIsLoading(false);  // Reset loading so user can interact with checkpoint
        } catch (error) {
          console.error("Failed to fetch checkpoint:", error);
          setIsLoading(false);  // Also reset on error
        }
      }
    },
    onComplete: () => {
      setAppState('complete');
      setIsLoading(false);
    },
    onError: (message) => {
      console.error("Workflow error:", message.data.message);
      setLogs((prev) => [...prev, message]);
      setIsLoading(false);
    },
  });

  // Handlers
  const handleStartAnalysis = async (transcript: string) => {
    setIsLoading(true);
    
    // Generate thread_id first
    const threadId = crypto.randomUUID();
    setThreadId(threadId);
    setAppState('processing');
    setCurrentStep('extracting');
    setProgressPercentage(0);
    setLogs([]); // Clear previous logs
    
    // Wait for WebSocket to connect, then send start message
    waitForConnection().then((connected) => {
      if (!connected) {
        alert("WebSocket connection failed. Please try again.");
        setAppState('input');
        setThreadId(null);
        setIsLoading(false);
        return;
      }
      
      const sent = sendMessage({
        type: "start",
        transcript: transcript
      });
      
      if (!sent) {
        alert("Failed to send start message. Please try again.");
        setAppState('input');
        setThreadId(null);
        setIsLoading(false);
      }
    });
  };

  const handleApproveCheckpoint = async (approvedIndices: number[], notes: string) => {
    if (!threadId) return;

    setIsLoading(true);
    setAppState('processing');
    setCurrentStep('writing');
    setProgressPercentage(90);
    
    // Send resume message via WebSocket (instead of REST API)
    const sent = sendMessage({
      type: "resume",
      approved_sources: approvedIndices,
      manual_notes: notes
    });
    
    if (!sent) {
      alert("Failed to send resume message. Please try again.");
      setIsLoading(false);
    }
    // Note: Progress will be updated via WebSocket messages from writer node
    // isLoading will be reset when complete message is received via onComplete callback
  };

  const handleAbortCheckpoint = () => {
    if (confirm("Are you sure you want to abort this analysis?")) {
      window.location.reload();
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <header className="bg-gray-900/50 backdrop-blur-xl border-b border-gray-800 shadow-2xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Building2 className="w-8 h-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">
                Hoxton Tax Limited
              </h1>
              <p className="text-sm text-gray-400">
                AI Tax Consultancy System
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Input State */}
        {appState === 'input' && (
          <div className="space-y-8">
            <p className="text-center text-xl text-gray-400 max-w-3xl mx-auto">
              Upload a client conversation to generate a comprehensive tax report
            </p>
            <TranscriptInput
              onSubmit={handleStartAnalysis}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Processing State - Keep visible even when complete */}
        {(appState === 'processing' || appState === 'checkpoint' || appState === 'complete') && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column - Progress */}
            <div className="lg:col-span-1 space-y-6">
              <div className="bg-gray-900/50 backdrop-blur-xl rounded-xl shadow-2xl border border-gray-800 p-6">
                <ProgressTracker
                  currentStep={currentStep}
                  progressPercentage={progressPercentage}
                />
              </div>
            </div>

            {/* Right Column - Terminal */}
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-gray-900/50 backdrop-blur-xl rounded-xl shadow-2xl border border-gray-800 p-6">
                <h3 className="text-lg font-semibold text-white mb-4">
                  Real-time Logs
                </h3>
                <TerminalLogs logs={logs} />
              </div>

              {appState === 'checkpoint' && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-5 backdrop-blur-sm">
                  <p className="text-yellow-400 font-semibold text-lg">
                    ⏸️ Checkpoint Reached - Review Required
                  </p>
                  <p className="text-sm text-yellow-300/80 mt-2">
                    Please review the research results in the panel on the right →
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Complete State - Appears below processing UI */}
        {appState === 'complete' && threadId && (
          <div 
            id="completion-section" 
            ref={completionRef}
            className="mt-12 space-y-12"
          >
            <div className="text-center space-y-4">
              <h2 className="text-5xl font-bold text-white tracking-tight">
                Analysis Complete
              </h2>
              <p className="mt-4 text-xl text-gray-400">
                Your professional tax report is ready
              </p>
            </div>
            <ReportViewer threadId={threadId} />
          </div>
        )}
      </div>

      {/* Checkpoint Review Panel */}
      <CheckpointReview
        isOpen={appState === 'checkpoint'}
        checkpointData={checkpointData}
        onApprove={handleApproveCheckpoint}
        onAbort={handleAbortCheckpoint}
        isLoading={isLoading}
      />

      {/* Footer */}
      <footer className="bg-gray-900/50 backdrop-blur-xl border-t border-gray-800 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-sm text-gray-500">
            © 2024 Hoxton Tax Limited - Professional Tax Consultancy Services
          </p>
        </div>
      </footer>
    </main>
  );
}

