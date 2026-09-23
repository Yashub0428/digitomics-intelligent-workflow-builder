import type { Ambiguity, ConversationStatus, MissingField, WorkflowState, GeneratedWorkflow } from './workflow';


export type MessageRole = 'user' | 'assistant';

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ConversationCreateResponse {
  conversation_id: string;
  phase: string;
  created_at: string;
  initial_state: WorkflowState;
}

export interface ConversationTurnResult {
  conversation_id: string;
  assistant_message: string;
  status: ConversationStatus;
  workflow?: GeneratedWorkflow | null;
  missing_information: MissingField[];
  ambiguity?: Ambiguity | null;
  state: WorkflowState;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
