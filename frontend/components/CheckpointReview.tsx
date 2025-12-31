"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import type { CheckpointData } from "@/types";

interface CheckpointReviewProps {
  isOpen: boolean;
  checkpointData: CheckpointData | null;
  onApprove: (approvedIndices: number[], notes: string) => void;
  onAbort: () => void;
  isLoading?: boolean;
}

export default function CheckpointReview({
  isOpen,
  checkpointData,
  onApprove,
  onAbort,
  isLoading = false,
}: CheckpointReviewProps) {
  const [selectedSources, setSelectedSources] = useState<Set<number>>(new Set());
  const [manualNotes, setManualNotes] = useState("");

  // Initialize all sources as selected when data loads
  useState(() => {
    if (checkpointData) {
      setSelectedSources(
        new Set(checkpointData.sources.map((s) => s.index))
      );
    }
  });

  const toggleSource = (index: number) => {
    const newSelected = new Set(selectedSources);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedSources(newSelected);
  };

  const handleApprove = () => {
    onApprove(Array.from(selectedSources), manualNotes);
  };

  if (!checkpointData) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 bg-black z-40"
            onClick={onAbort}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="fixed right-0 top-0 h-full w-full md:w-[520px] bg-gray-900 shadow-2xl z-50 flex flex-col border-l border-gray-800"
          >
            {/* Header */}
            <div className="px-6 py-5 border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">
                    Review Research Results
                  </h2>
                  <p className="text-sm text-gray-400 mt-1">
                    {checkpointData.profile.client_name} - {checkpointData.sources.length} sources found
                  </p>
                </div>
                <button
                  onClick={onAbort}
                  disabled={isLoading}
                  className="p-2 hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
              {/* Client Summary */}
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-5 space-y-3 backdrop-blur-sm">
                <div className="font-semibold text-blue-400 text-lg">Client Scenario</div>
                <div className="text-sm text-blue-200/80 space-y-2">
                  <div>
                    <strong className="text-blue-300">Current:</strong> {checkpointData.profile.tax_residency_current}
                  </div>
                  <div>
                    <strong className="text-blue-300">Target:</strong> {checkpointData.profile.tax_residency_target || "N/A"}
                  </div>
                  <div>
                    <strong className="text-blue-300">Assets:</strong> {checkpointData.profile.assets.join(", ")}
                  </div>
                </div>
              </div>

              {/* Research Queries */}
              <div>
                <h3 className="font-semibold text-white mb-3">Research Queries</h3>
                <div className="text-sm text-gray-400 space-y-2">
                  {checkpointData.researchPlan.queries.map((query, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-gray-600 font-mono">{i + 1}.</span>
                      <span>{query}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sources */}
              <div>
                <h3 className="font-semibold text-white mb-4">
                  Sources ({selectedSources.size}/{checkpointData.sources.length} selected)
                </h3>
                <div className="space-y-3 max-h-80 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-gray-900">
                  {checkpointData.sources.map((source) => {
                    const isSelected = selectedSources.has(source.index);
                    return (
                      <div
                        key={source.index}
                        onClick={() => toggleSource(source.index)}
                        className={`p-4 border-2 rounded-xl cursor-pointer transition-all ${
                          isSelected
                            ? "border-green-500/50 bg-green-500/10 hover:bg-green-500/15"
                            : "border-gray-800 bg-gray-950/30 hover:border-gray-700"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className="pt-1">
                            {isSelected ? (
                              <CheckCircle className="w-5 h-5 text-green-400" />
                            ) : (
                              <XCircle className="w-5 h-5 text-gray-600" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-sm text-white truncate">
                              {source.title}
                            </div>
                            <div className="text-xs text-gray-500 truncate mt-1 font-mono">
                              {source.url}
                            </div>
                            <div className="text-sm text-gray-400 mt-2 line-clamp-2">
                              {source.snippet}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Manual Notes */}
              <div>
                <label htmlFor="notes" className="block font-semibold text-white mb-3">
                  Additional Notes (Optional)
                </label>
                <textarea
                  id="notes"
                  value={manualNotes}
                  onChange={(e) => setManualNotes(e.target.value)}
                  disabled={isLoading}
                  placeholder="Add any manual research notes or additional documents..."
                  className="w-full min-h-[100px] px-4 py-3 bg-gray-950/50 border-2 border-gray-800 rounded-xl
                    focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50
                    disabled:opacity-50 text-sm text-gray-200 placeholder:text-gray-600 resize-none
                    transition-all"
                />
              </div>

              {/* Warning */}
              {selectedSources.size === 0 && (
                <div className="flex items-start gap-3 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl backdrop-blur-sm">
                  <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-yellow-200/80">
                    <strong className="text-yellow-300">Warning:</strong> No sources selected. The report will be generated
                    without research context.
                  </div>
                </div>
              )}
            </div>

            {/* Footer Actions */}
            <div className="px-6 py-5 border-t border-gray-800 bg-gray-900/50 backdrop-blur-xl space-y-3">
              <button
                onClick={handleApprove}
                disabled={isLoading}
                className="w-full px-6 py-4 bg-primary text-white rounded-xl font-semibold text-lg
                  hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20
                  focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 focus:ring-offset-gray-900
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all shadow-xl"
              >
                {isLoading ? "Generating Report..." : "Approve & Continue"}
              </button>
              <button
                onClick={onAbort}
                disabled={isLoading}
                className="w-full px-6 py-3 text-gray-300 rounded-xl font-semibold border-2 border-gray-700
                  hover:bg-gray-800 hover:border-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-600 focus:ring-offset-2 focus:ring-offset-gray-900
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all"
              >
                Abort Analysis
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

