export type ConversationStatus = 'COLLECTING' | 'READY' | 'GENERATED';

export interface Intent {
  summary: string | null;
  tags?: string[];
}

export interface TriggerSource {
  kind: string | null;
  identifier: string | null;
  parameters?: Record<string, unknown>;
}

export interface Trigger {
  kind: string | null;
  parameters?: Record<string, unknown>;
}

export interface Schedule {
  frequency: string | null;
  cron: string | null;
  timezone: string | null;
  parameters?: Record<string, unknown>;
}

export interface Condition {
  id: string;
  expression: string | null;
  parameters?: Record<string, unknown>;
}

export interface Action {
  id: string;
  kind: string | null;
  parameters: Record<string, unknown>;
  needs_recipients?: boolean;
  required_parameters?: string[];
}

export interface Recipient {
  id: string;
  channel: string | null;
  address: string | null;
  parameters?: Record<string, unknown>;
}

export interface Preferences {
  timezone?: string | null;
  language?: string | null;
  [key: string]: unknown;
}

export interface MissingField {
  path: string;
  reason: string;
}

export interface AmbiguityOption {
  id: string;
  label: string;
}

export interface Ambiguity {
  id: string;
  path: string;
  question: string;
  options: AmbiguityOption[];
  resolved: boolean;
  chosen: string | null;
}

export interface WorkflowState {
  schema_version: number;
  status: ConversationStatus;
  intent: Intent;
  trigger: Trigger;
  trigger_source: TriggerSource;
  schedule?: Schedule | null;
  conditions: Condition[];
  actions: Action[];
  recipients: Recipient[];
  preferences: Preferences;
  collected?: Record<string, { path: string; value: unknown; utterance_id?: string; updated_at?: string }>;
  missing_mandatory_fields: MissingField[];
  ambiguities: Ambiguity[];
}

export interface GeneratedWorkflow {
  id: string;
  name: string;
  status: string;
  schema_version: number;
  intent: Record<string, unknown>;
  trigger: {
    kind: string | null;
    source?: Record<string, unknown> | null;
    schedule?: Record<string, unknown> | null;
    parameters?: Record<string, unknown>;
  };
  conditions: Array<Record<string, unknown>>;
  actions: Array<Record<string, unknown>>;
  recipients: Array<Record<string, unknown>>;
  preferences?: Record<string, unknown>;
}
