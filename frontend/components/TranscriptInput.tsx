"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

interface TranscriptInputProps {
  onSubmit: (transcript: string) => void;
  isLoading?: boolean;
}

const EXAMPLE_TRANSCRIPT = `Advisor: Hi Simon, good to speak again. We need to finalize your move plan.
Simon: Yes. I'm definitely moving to Saudi Arabia (KSA) on September 1st.
Advisor: Okay. And the family?
Simon: My wife Suong is staying in our London home for another year for the kids' school.
Advisor: That makes the "Main Residence" test tricky. What about the pension?
Simon: I have £1.2m in a UK SIPP. I want to withdraw it all once I'm resident in KSA.
I heard the tax treaty Article 18 says it's taxable only in KSA, which is 0% tax. Can you confirm?
Advisor: I'll check the treaty. Any other UK ties?
Simon: I'll come back to the UK for maybe 45 days a year to visit Suong.`;

export default function TranscriptInput({ onSubmit, isLoading = false }: TranscriptInputProps) {
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = () => {
    setError("");

    // Validation
    if (transcript.trim().length < 50) {
      setError("Please provide a valid conversation transcript (min. 50 characters)");
      return;
    }

    if (!transcript.includes(":")) {
      setError("Transcript should be in dialogue format (e.g., 'Advisor: ... Client: ...')");
      return;
    }

    onSubmit(transcript);
  };

  const handleLoadExample = () => {
    setTranscript(EXAMPLE_TRANSCRIPT);
    setError("");
  };

  const charCount = transcript.length;
  const isValid = charCount >= 50 && transcript.includes(":");

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      <div className="bg-gray-900/50 backdrop-blur-xl rounded-2xl shadow-2xl border border-gray-800 p-8 space-y-6">
        <div className="flex items-center justify-between">
          <label htmlFor="transcript" className="text-base font-semibold text-white">
            Client Conversation Transcript
          </label>
          <button
            onClick={handleLoadExample}
            disabled={isLoading}
            className="text-sm text-emerald-400 hover:text-emerald-300 font-medium transition-colors disabled:opacity-50"
          >
            Load Example
          </button>
        </div>

        <textarea
          id="transcript"
          value={transcript}
          onChange={(e) => {
            setTranscript(e.target.value);
            setError("");
          }}
          disabled={isLoading}
          placeholder="Paste the conversation transcript here...

Example format:
Advisor: Hi, let's discuss your tax situation.
Client: I'm moving to Saudi Arabia next month..."
          className={`w-full h-72 px-5 py-4 bg-gray-800 rounded-xl border-2 transition-all font-mono text-sm text-gray-100 placeholder:text-gray-500
            ${error ? "border-red-500/50 bg-red-500/5" : isValid ? "border-emerald-500/50 bg-emerald-500/5" : "border-gray-700"}
            focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50
            disabled:opacity-50 disabled:cursor-not-allowed
            resize-none shadow-inner`}
        />

        {error && (
          <div className="text-sm text-red-400 font-medium">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!isValid || isLoading}
          className="w-full px-8 py-4 bg-emerald-500 text-white rounded-xl font-semibold text-lg
            hover:bg-emerald-600 hover:shadow-lg hover:shadow-emerald-500/20
            focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:ring-offset-2 focus:ring-offset-gray-900
            disabled:opacity-40 disabled:cursor-not-allowed
            transition-all duration-200
            flex items-center justify-center gap-3
            shadow-xl"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-6 h-6 animate-spin" />
              Starting Analysis...
            </>
          ) : (
            "Start Tax Analysis"
          )}
        </button>
      </div>
    </div>
  );
}

