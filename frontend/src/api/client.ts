import type {
  ConversationCreateResponse,
  ConversationMessage,
  ConversationTurnResult,
} from '../types/conversation';
import type { GeneratedWorkflow, WorkflowState } from '../types/workflow';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}


async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorData;
      try {
        errorData = await res.json();
      } catch {
        // Response was not JSON
      }

      const message =
        errorData?.error?.message ||
        errorData?.detail ||
        `Request failed with status ${res.status}`;
      const code = errorData?.error?.code || 'api_error';
      const details = errorData?.error?.details;

      throw new ApiError(res.status, code, message, details);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Network error or backend unavailable';
    throw new ApiError(0, 'network_error', message);
  }
}

export const api = {
  createConversation: async (title?: string): Promise<ConversationCreateResponse> => {
    return request<ConversationCreateResponse>('/api/conversations', {
      method: 'POST',
      body: JSON.stringify(title ? { title } : {}),
    });
  },

  sendMessage: async (
    conversationId: string,
    content: string
  ): Promise<ConversationTurnResult> => {
    return request<ConversationTurnResult>(`/api/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },

  getMessages: async (conversationId: string): Promise<ConversationMessage[]> => {
    return request<ConversationMessage[]>(`/api/conversations/${conversationId}/messages`, {
      method: 'GET',
    });
  },

  getState: async (conversationId: string): Promise<{ conversation_id: string; state: WorkflowState }> => {
    return request<{ conversation_id: string; state: WorkflowState }>(
      `/api/conversations/${conversationId}/state`,
      { method: 'GET' }
    );
  },

  getWorkflow: async (
    conversationId: string
  ): Promise<{ conversation_id: string; status: string; workflow: GeneratedWorkflow }> => {
    return request<{ conversation_id: string; status: string; workflow: GeneratedWorkflow }>(
      `/api/conversations/${conversationId}/workflow`,
      { method: 'GET' }
    );
  },
};
