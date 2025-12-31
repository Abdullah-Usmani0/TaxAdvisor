/**
 * TypeScript type definitions for Hoxton Tax AI
 */

export interface AnalysisStatus {
  threadId: string;
  currentStep: 'extracting' | 'planning' | 'researching' | 'checkpoint' | 'writing' | 'complete' | 'error';
  progressPercentage: number;
  isPaused: boolean;
  error?: string;
}

export interface ResearchSource {
  index: number;
  url: string;
  title: string;
  snippet: string;
  relevanceScore?: number;
}

export interface CheckpointData {
  threadId: string;
  profile: ClientProfile;
  researchPlan: ResearchPlan;
  sources: ResearchSource[];
  timestamp: string;
}

export interface ClientProfile {
  client_name: string;
  tax_residency_current: string;
  tax_residency_target?: string;
  assets: string[];
  marital_status: string;
  specific_goals: string[];
}

export interface ResearchPlan {
  queries: string[];
  rationale: string;
}

export interface WSLogMessage {
  type: 'log' | 'progress' | 'checkpoint' | 'complete' | 'error';
  timestamp: string;
  data: {
    message: string;
    log_type?: 'info' | 'success' | 'error';
    current_step?: string;
    progress_percentage?: number;
  };
}

export interface AnalyzeRequest {
  transcript: string;
}

export interface AnalyzeResponse {
  thread_id: string;
  status: string;
  message: string;
}

export interface CheckpointApprovalRequest {
  thread_id: string;
  approved_sources: number[];
  manual_notes?: string;
  action: 'approve' | 'refine' | 'abort';
}

