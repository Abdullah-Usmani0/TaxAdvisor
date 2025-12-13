"use client";

import { motion } from "framer-motion";
import { CheckCircle, Circle, Loader2 } from "lucide-react";

interface Step {
  id: string;
  label: string;
  description: string;
}

interface ProgressTrackerProps {
  currentStep: string;
  progressPercentage: number;
}

const STEPS: Step[] = [
  {
    id: "extracting",
    label: "Extract Profile",
    description: "Analyzing transcript",
  },
  {
    id: "planning",
    label: "Plan Research",
    description: "Creating strategy",
  },
  {
    id: "researching",
    label: "Execute Research",
    description: "Searching legislation",
  },
  {
    id: "writing",
    label: "Write Report",
    description: "Generating analysis",
  },
];

export default function ProgressTracker({
  currentStep,
  progressPercentage,
}: ProgressTrackerProps) {
  const getStepStatus = (stepId: string): "completed" | "in-progress" | "pending" => {
    const stepIndex = STEPS.findIndex((s) => s.id === stepId);
    const currentIndex = STEPS.findIndex((s) => s.id === currentStep);

    if (currentIndex === -1) return "pending";
    if (stepIndex < currentIndex) return "completed";
    if (stepIndex === currentIndex) return "in-progress";
    return "pending";
  };

  return (
    <div className="w-full space-y-6">
      {/* Circular Progress Indicator */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Analysis Progress</h3>
        <div className="relative w-20 h-20">
          <svg className="w-full h-full transform -rotate-90">
            {/* Background circle */}
            <circle
              cx="40"
              cy="40"
              r="32"
              stroke="currentColor"
              strokeWidth="6"
              fill="none"
              className="text-gray-800"
            />
            {/* Progress circle */}
            <motion.circle
              cx="40"
              cy="40"
              r="32"
              stroke="currentColor"
              strokeWidth="6"
              fill="none"
              strokeLinecap="round"
              className="text-primary drop-shadow-[0_0_8px_rgba(26,77,46,0.5)]"
              initial={{ strokeDashoffset: 200.96 }}
              animate={{
                strokeDashoffset: 200.96 - (200.96 * progressPercentage) / 100,
              }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              style={{
                strokeDasharray: "200.96 200.96",
              }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-white">
              {progressPercentage}%
            </span>
          </div>
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-4">
        {STEPS.map((step, index) => {
          const status = getStepStatus(step.id);
          const isLast = index === STEPS.length - 1;

          return (
            <div key={step.id} className="relative">
              <div className="flex items-start gap-4">
                {/* Step Icon */}
                <div className="relative flex-shrink-0">
                  {status === "completed" && (
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                    >
                      <CheckCircle className="w-8 h-8 text-green-500" />
                    </motion.div>
                  )}
                  {status === "in-progress" && (
                    <div className="relative">
                      <Circle className="w-8 h-8 text-orange-500 animate-pulse drop-shadow-[0_0_8px_rgba(249,115,22,0.5)]" />
                      <Loader2 className="w-5 h-5 text-orange-500 animate-spin absolute top-1.5 left-1.5" />
                    </div>
                  )}
                  {status === "pending" && (
                    <Circle className="w-8 h-8 text-gray-700 opacity-40" />
                  )}

                  {/* Connector Line */}
                  {!isLast && (
                    <div
                      className={`absolute left-4 top-8 w-0.5 h-10 ${
                        status === "completed"
                          ? "bg-green-500"
                          : "bg-gray-800 border-dashed"
                      }`}
                      style={{
                        borderLeftWidth: status === "completed" ? 0 : 2,
                        borderLeftStyle: status === "completed" ? "solid" : "dashed",
                      }}
                    />
                  )}
                </div>

                {/* Step Content */}
                <div className="flex-1 pt-1">
                  <div
                    className={`font-semibold ${
                      status === "in-progress"
                        ? "text-white"
                        : status === "completed"
                        ? "text-gray-300"
                        : "text-gray-600"
                    }`}
                  >
                    {step.label}
                  </div>
                  <div
                    className={`text-sm ${
                      status === "in-progress"
                        ? "text-gray-400"
                        : "text-gray-600"
                    }`}
                  >
                    {step.description}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

