"use client";

import { Download, FileText, CheckCircle } from "lucide-react";
import { getDownloadUrl } from "@/lib/api";

interface ReportViewerProps {
  threadId: string;
  reportMarkdown?: string;
}

export default function ReportViewer({ threadId, reportMarkdown }: ReportViewerProps) {
  const handleDownload = () => {
    const downloadUrl = getDownloadUrl(threadId);
    window.open(downloadUrl, "_blank");
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      {/* Success Banner */}
      <div className="bg-green-500/10 border-2 border-green-500/30 rounded-xl p-8 backdrop-blur-sm">
        <div className="flex items-center gap-6">
          <div className="flex-shrink-0">
            <CheckCircle className="w-16 h-16 text-green-400 drop-shadow-[0_0_12px_rgba(74,222,128,0.5)]" />
          </div>
          <div className="flex-1">
            <h3 className="text-2xl font-bold text-white">
              Report Generated Successfully!
            </h3>
            <p className="text-green-300/80 mt-2 text-lg">
              Your comprehensive tax analysis report is ready for download.
            </p>
          </div>
        </div>
      </div>

      {/* Download Card */}
      <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-8 space-y-6 shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/10 rounded-xl">
            <FileText className="w-10 h-10 text-primary" />
          </div>
          <div className="flex-1">
            <h4 className="text-xl font-bold text-white">Tax Residency & Planning Report</h4>
            <p className="text-sm text-gray-400 mt-1">
              Professional PDF with Hoxton Tax branding
            </p>
          </div>
        </div>

        <button
          onClick={handleDownload}
          className="w-full px-8 py-4 bg-primary text-white rounded-xl font-semibold text-lg
            hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
            focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-gray-900
            transition-all duration-200
            flex items-center justify-center gap-3
            shadow-xl"
        >
          <Download className="w-6 h-6" />
          Download PDF Report
        </button>

        <p className="text-xs text-gray-600 text-center font-mono">
          Report ID: {threadId.substring(0, 8)}...
        </p>
      </div>

      {/* Report Preview (if markdown available) */}
      {reportMarkdown && (
        <div className="bg-gray-900/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-8 shadow-2xl">
          <h4 className="text-xl font-bold text-white mb-6">Report Preview</h4>
          <div className="prose prose-sm max-w-none">
            <div className="text-gray-300 font-mono text-xs bg-gray-950/50 p-6 rounded-xl border border-gray-800 max-h-96 overflow-y-auto whitespace-pre-wrap">
              {reportMarkdown.substring(0, 1000)}
              {reportMarkdown.length > 1000 && "\n\n... (truncated for preview)"}
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-4">
        <button
          onClick={() => window.location.reload()}
          className="flex-1 px-6 py-3 border-2 border-gray-700 text-gray-300 rounded-xl font-semibold
            hover:bg-gray-800 hover:border-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600 focus:ring-offset-2 focus:ring-offset-gray-900
            transition-all"
        >
          Start New Analysis
        </button>
      </div>
    </div>
  );
}

