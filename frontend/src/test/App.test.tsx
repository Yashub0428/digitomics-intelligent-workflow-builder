import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';
import { api } from '../api/client';
import type { WorkflowState, GeneratedWorkflow } from '../types/workflow';
import type { ConversationTurnResult } from '../types/conversation';

vi.mock('../api/client', () => ({
  api: {
    createConversation: vi.fn(),
    sendMessage: vi.fn(),
    getMessages: vi.fn(),
    getState: vi.fn(),
    getWorkflow: vi.fn(),
  },
}));

const mockInitialState: WorkflowState = {
  schema_version: 1,
  status: 'COLLECTING',
  intent: { summary: null, tags: [] },
  trigger: { kind: null, parameters: {} },
  trigger_source: { kind: null, identifier: null, parameters: {} },
  schedule: null,
  conditions: [],
  actions: [],
  recipients: [],
  preferences: {},
  missing_mandatory_fields: [
    { path: 'intent.summary', reason: 'User intent is required' },
    { path: 'trigger.kind', reason: 'A trigger kind is required' },
    { path: 'actions', reason: 'At least one action is required' },
  ],
  ambiguities: [],
};

const mockGeneratedWorkflow: GeneratedWorkflow = {
  id: 'wf_test123',
  name: 'Send Slack alert on Stripe order',
  status: 'ready',
  schema_version: 1,
  intent: { summary: 'Send Slack alert on Stripe order' },
  trigger: { kind: 'order.created', parameters: {} },
  conditions: [],
  actions: [{ kind: 'slack.message', parameters: { channel: '#sales' } }],
  recipients: [],
};

describe('Conversational Workflow Builder Frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.createConversation).mockResolvedValue({
      conversation_id: 'conv_123',
      phase: 'COLLECTING',
      created_at: new Date().toISOString(),
      initial_state: mockInitialState,
    });
  });

  it('1. Empty state renders on initial load', async () => {
    render(<App />);

    expect(
      await screen.findByText(/Describe the automation you want to build/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/When I receive a new invoice, notify the finance team/i)
    ).toBeInTheDocument();
  });

  it('2. User can type a message into the input', async () => {
    render(<App />);
    const textarea = (await screen.findByPlaceholderText(
      /Type your message/i
    )) as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: 'Sync orders to sheets' } });
    expect(textarea.value).toBe('Sync orders to sheets');
  });

  it('3. Send button is disabled for empty or whitespace input', async () => {
    render(<App />);
    const button = (await screen.findByTitle(/Send message/i)) as HTMLButtonElement;
    expect(button).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: '   ' } });
    expect(button).toBeDisabled();

    fireEvent.change(textarea, { target: { value: 'Non-empty' } });
    expect(button).not.toBeDisabled();
  });

  it('4. User message appears after successful send', async () => {
    vi.mocked(api.sendMessage).mockResolvedValue({
      conversation_id: 'conv_123',
      assistant_message: 'Which platform should trigger the workflow?',
      status: 'COLLECTING',
      missing_information: [{ path: 'trigger_source', reason: 'Source needed' }],
      state: {
        ...mockInitialState,
        intent: { summary: 'Send notifications' },
      },
    });

    render(<App />);
    const textarea = await screen.findByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: 'I want to send notifications' } });

    const sendButton = screen.getByTitle(/Send message/i);
    fireEvent.click(sendButton);

    expect(await screen.findByText('I want to send notifications')).toBeInTheDocument();
  });

  it('5. Assistant response appears in conversation', async () => {
    vi.mocked(api.sendMessage).mockResolvedValue({
      conversation_id: 'conv_123',
      assistant_message: 'Which platform should trigger the workflow?',
      status: 'COLLECTING',
      missing_information: [],
      state: mockInitialState,
    });

    render(<App />);
    const textarea = await screen.findByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: 'Notify me' } });
    fireEvent.click(screen.getByTitle(/Send message/i));

    expect(
      await screen.findByText('Which platform should trigger the workflow?')
    ).toBeInTheDocument();
  });

  it('6. Loading state appears while waiting for assistant', async () => {
    let resolveMessage: (value: ConversationTurnResult) => void;
    const promise = new Promise<ConversationTurnResult>((resolve) => {
      resolveMessage = resolve;
    });
    vi.mocked(api.sendMessage).mockReturnValue(promise);

    render(<App />);
    const textarea = await screen.findByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: 'Hello assistant' } });
    fireEvent.click(screen.getByTitle(/Send message/i));

    expect(
      screen.getByText(/Analyzing requirements and checking workflow completeness/i)
    ).toBeInTheDocument();

    resolveMessage!({
      conversation_id: 'conv_123',
      assistant_message: 'Here is your clarification',
      status: 'COLLECTING',
      missing_information: [],
      state: mockInitialState,
    });

    expect(await screen.findByText('Here is your clarification')).toBeInTheDocument();
    expect(
      screen.queryByText(/Analyzing requirements and checking workflow completeness/i)
    ).not.toBeInTheDocument();
  });

  it('7. Workflow state panel updates after message', async () => {
    vi.mocked(api.sendMessage).mockResolvedValue({
      conversation_id: 'conv_123',
      assistant_message: 'Where should notifications be sent?',
      status: 'COLLECTING',
      missing_information: [{ path: 'recipients', reason: 'Recipient needed' }],
      state: {
        ...mockInitialState,
        intent: { summary: 'Monitor GitHub issues' },
        trigger: { kind: 'github.issue_opened', parameters: {} },
        missing_mandatory_fields: [{ path: 'recipients', reason: 'Recipient needed' }],
      },
    });

    render(<App />);
    const textarea = await screen.findByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: 'Monitor GitHub issues' } });
    fireEvent.click(screen.getByTitle(/Send message/i));

    expect(await screen.findByText('Monitor GitHub issues')).toBeInTheDocument();
    expect(screen.getByText('github.issue_opened')).toBeInTheDocument();
    expect(screen.getByText(/Recipient needed/i)).toBeInTheDocument();
  });

  it('8. Generated workflow appears when backend returns one', async () => {
    vi.mocked(api.sendMessage).mockResolvedValue({
      conversation_id: 'conv_123',
      assistant_message: 'Workflow completed successfully.',
      status: 'GENERATED',
      workflow: mockGeneratedWorkflow,
      missing_information: [],
      state: {
        ...mockInitialState,
        status: 'GENERATED',
        intent: { summary: 'Send Slack alert on Stripe order' },
      },
    });

    render(<App />);
    const textarea = await screen.findByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: 'Complete flow' } });
    fireEvent.click(screen.getByTitle(/Send message/i));

    expect(await screen.findByText(/View Generated Workflow/i)).toBeInTheDocument();

    // Click to open modal
    fireEvent.click(screen.getByText(/View Generated Workflow/i));
    expect(screen.getByText('Workflow Specification Generated')).toBeInTheDocument();
    expect(screen.getAllByText(/Send Slack alert on Stripe order/i).length).toBeGreaterThan(0);
  });

  it('9. Error state is displayed for API failure', async () => {
    vi.mocked(api.sendMessage).mockRejectedValue(new Error('Network connection dropped'));

    render(<App />);
    const textarea = await screen.findByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: 'Send request' } });
    fireEvent.click(screen.getByTitle(/Send message/i));

    expect(
      await screen.findByText('Network connection dropped')
    ).toBeInTheDocument();
  });

  it('10. New Workflow resets the conversation', async () => {
    render(<App />);
    expect(await screen.findByText(/Describe the automation/i)).toBeInTheDocument();

    const newBtn = screen.getByText('New Workflow');
    fireEvent.click(newBtn);

    await waitFor(() => {
      expect(api.createConversation).toHaveBeenCalledTimes(2);
    });
  });

  it('11. Generated workflow modal switches between Visual and JSON tabs', async () => {
    vi.mocked(api.sendMessage).mockResolvedValue({
      conversation_id: 'conv_123',
      assistant_message: 'Workflow generated.',
      status: 'GENERATED',
      workflow: mockGeneratedWorkflow,
      missing_information: [],
      state: {
        ...mockInitialState,
        status: 'GENERATED',
        intent: { summary: 'Send Slack alert on Stripe order' },
      },
    });

    render(<App />);
    const textarea = await screen.findByPlaceholderText(/Type your message/i);
    fireEvent.change(textarea, { target: { value: 'Finish' } });
    fireEvent.click(screen.getByTitle(/Send message/i));

    // Open modal
    const viewBtn = await screen.findByText(/View Generated Workflow/i);
    fireEvent.click(viewBtn);

    // Initial default tab is Visual
    expect(screen.getByText('Visual')).toBeInTheDocument();
    expect(screen.getByText('JSON')).toBeInTheDocument();
    expect(screen.getByText(/Read-only graph visualization/i)).toBeInTheDocument();

    // Switch to JSON tab
    fireEvent.click(screen.getByText('JSON'));
    expect(screen.getByText('Copy JSON')).toBeInTheDocument();
    expect(screen.getByText('Download')).toBeInTheDocument();
    expect(screen.getByText(/Read-only JSON representation directly generated by backend/i)).toBeInTheDocument();

    // Switch back to Visual tab
    fireEvent.click(screen.getByText('Visual'));
    expect(screen.getByText(/Read-only graph visualization/i)).toBeInTheDocument();
  });
});

