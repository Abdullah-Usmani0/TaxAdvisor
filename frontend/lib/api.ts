/**
 * API client functions for backend communication
 */
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  AnalysisStatus,
  CheckpointData,
  CheckpointApprovalRequest,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function startAnalysis(
  transcript: string
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ transcript } as AnalyzeRequest),
  });

  if (!response.ok) {
    throw new Error(`Analysis failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getStatus(threadId: string): Promise<AnalysisStatus> {
  const response = await fetch(`${API_URL}/api/status/${threadId}`);

  if (!response.ok) {
    throw new Error(`Status fetch failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getCheckpoint(threadId: string): Promise<CheckpointData> {
  const response = await fetch(`${API_URL}/api/checkpoint/${threadId}`);

  if (!response.ok) {
    throw new Error(`Checkpoint fetch failed: ${response.statusText}`);
  }

  return response.json();
}

export async function approveCheckpoint(
  request: CheckpointApprovalRequest
): Promise<{ status: string; report_ready: boolean; message: string }> {
  const response = await fetch(`${API_URL}/api/checkpoint/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Approval failed: ${response.statusText}`);
  }

  return response.json();
}

export function getDownloadUrl(threadId: string): string {
  return `${API_URL}/api/download/${threadId}`;
}

