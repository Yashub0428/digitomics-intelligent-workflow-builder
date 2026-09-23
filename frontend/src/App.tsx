import { useState, useEffect, useCallback } from 'react';
import { api } from './api/client';
import type { ConversationMessage } from './types/conversation';
import type { WorkflowState, GeneratedWorkflow } from './types/workflow';

import { Header } from './components/Header';
import { ConversationPanel } from './components/Chat/ConversationPanel';
import { WorkflowStatePanel } from './components/Workflow/WorkflowStatePanel';
import { WorkflowModal } from './components/Workflow/WorkflowModal';
import { ErrorBanner } from './components/common/ErrorBanner';

export function App() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [workflowState, setWorkflowState] = useState<WorkflowState | null>(null);
  const [generatedWorkflow, setGeneratedWorkflow] = useState<GeneratedWorkflow | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [ambiguityOptions, setAmbiguityOptions] = useState<string[]>([]);

  // Initialize a new conversation
  const handleNewWorkflow = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setAmbiguityOptions([]);
    setGeneratedWorkflow(null);

    try {
      const res = await api.createConversation();
      setConversationId(res.conversation_id);
      setMessages([]);
      setWorkflowState(res.initial_state);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect to backend service';
      setError(`Could not initialize conversation: ${msg}. Make sure backend is running.`);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Mount effect to start initial conversation
  useEffect(() => {
    handleNewWorkflow();
  }, [handleNewWorkflow]);

  // Send message handler
  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

    if (!conversationId) {
      setError('No active conversation. Please click "New Workflow" to begin.');
      return;
    }

    const optimisticId = `user_${Date.now()}`;
    const userMessage: ConversationMessage = {
      id: optimisticId,
      conversation_id: conversationId,
      role: 'user',
      content: content.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    setAmbiguityOptions([]);

    try {
      const turnResult = await api.sendMessage(conversationId, content);

      // Create assistant message
      const assistantMessage: ConversationMessage = {
        id: `asst_${Date.now()}`,
        conversation_id: conversationId,
        role: 'assistant',
        content: turnResult.assistant_message,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      const nextState: WorkflowState = {
        ...turnResult.state,
        missing_mandatory_fields:
          turnResult.state?.missing_mandatory_fields && turnResult.state.missing_mandatory_fields.length > 0
            ? turnResult.state.missing_mandatory_fields
            : (turnResult.missing_information ?? []),
      };
      setWorkflowState(nextState);

      if (turnResult.workflow) {
        setGeneratedWorkflow(turnResult.workflow);
      }

      if (turnResult.ambiguity && turnResult.ambiguity.options?.length > 0) {
        setAmbiguityOptions(turnResult.ambiguity.options.map((opt) => opt.label));
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Something went wrong while processing your message. Please try again.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-100">
      {/* Global Header */}
      <Header
        status={workflowState?.status}
        onNewWorkflow={handleNewWorkflow}
        onViewWorkflow={() => setIsModalOpen(true)}
        hasWorkflow={!!generatedWorkflow}
        isLoading={isLoading}
      />

      {/* Dismissible Error Banner */}
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {/* Main Workspace Area */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left / Center: Conversational Assistant Panel */}
        <ConversationPanel
          messages={messages}
          isLoading={isLoading}
          onSendMessage={handleSendMessage}
          ambiguityOptions={ambiguityOptions}
          onSelectOption={handleSendMessage}
        />

        {/* Right: Structured Workflow State Panel */}
        <WorkflowStatePanel
          state={workflowState}
          onViewWorkflow={() => setIsModalOpen(true)}
        />
      </main>


      {/* Workflow JSON Specification Modal */}
      <WorkflowModal
        workflow={generatedWorkflow}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}

export default App;
