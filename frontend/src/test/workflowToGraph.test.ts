import { describe, it, expect } from 'vitest';
import { workflowToGraph } from '../components/Workflow/workflowToGraph';
import type { GeneratedWorkflow } from '../types/workflow';

describe('workflowToGraph transformation unit tests', () => {
  it('1. Trigger-only workflow creates trigger node and no edges', () => {
    const workflow: GeneratedWorkflow = {
      id: 'wf_1',
      name: 'Trigger Only',
      status: 'ready',
      schema_version: 1,
      intent: { summary: 'Listen for events' },
      trigger: {
        kind: 'webhook.received',
        source: { kind: 'github', identifier: 'repo-alerts' },
        schedule: null,
      },
      conditions: [],
      actions: [],
      recipients: [],
    };

    const { nodes, edges } = workflowToGraph(workflow);

    expect(nodes).toHaveLength(1);
    expect(nodes[0].id).toBe('trigger');
    expect(nodes[0].type).toBe('triggerNode');
    expect(nodes[0].data.kind).toBe('webhook.received');
    expect(edges).toHaveLength(0);
  });

  it('2. Trigger + action creates correct nodes and edge', () => {
    const workflow: GeneratedWorkflow = {
      id: 'wf_2',
      name: 'Trigger and Action',
      status: 'ready',
      schema_version: 1,
      intent: { summary: 'Post on event' },
      trigger: {
        kind: 'order.created',
      },
      conditions: [],
      actions: [
        {
          id: 'act_slack',
          kind: 'slack.message',
          parameters: { channel: '#sales' },
        },
      ],
      recipients: [],
    };

    const { nodes, edges } = workflowToGraph(workflow);

    expect(nodes).toHaveLength(2);
    expect(nodes.map((n) => n.id)).toEqual(['trigger', 'action-act_slack']);

    // Direct edge from trigger to action
    expect(edges).toHaveLength(1);
    expect(edges[0].source).toBe('trigger');
    expect(edges[0].target).toBe('action-act_slack');
  });

  it('3. Trigger + condition + action creates correct sequence', () => {
    const workflow: GeneratedWorkflow = {
      id: 'wf_3',
      name: 'Conditional Workflow',
      status: 'ready',
      schema_version: 1,
      intent: { summary: 'Alert on large orders' },
      trigger: {
        kind: 'order.created',
      },
      conditions: [
        {
          id: 'cond_high_value',
          expression: 'order.total > 500',
        },
      ],
      actions: [
        {
          id: 'act_pagerduty',
          kind: 'pagerduty.incident',
          parameters: { severity: 'high' },
        },
      ],
      recipients: [],
    };

    const { nodes, edges } = workflowToGraph(workflow);

    expect(nodes).toHaveLength(3);
    const nodeIds = nodes.map((n) => n.id);
    expect(nodeIds).toEqual(['trigger', 'condition-cond_high_value', 'action-act_pagerduty']);

    expect(edges).toHaveLength(2);
    // Trigger -> Condition
    expect(edges[0].source).toBe('trigger');
    expect(edges[0].target).toBe('condition-cond_high_value');
    // Condition -> Action
    expect(edges[1].source).toBe('condition-cond_high_value');
    expect(edges[1].target).toBe('action-act_pagerduty');
  });

  it('4. Multiple actions are represented with horizontal branching', () => {
    const workflow: GeneratedWorkflow = {
      id: 'wf_4',
      name: 'Multi-action Workflow',
      status: 'ready',
      schema_version: 1,
      intent: { summary: 'Broadcast alert' },
      trigger: {
        kind: 'incident.triggered',
      },
      conditions: [],
      actions: [
        {
          id: 'act_slack',
          kind: 'slack.message',
          parameters: { channel: '#war-room' },
        },
        {
          id: 'act_email',
          kind: 'email.send',
          parameters: { subject: 'Urgent Alert' },
        },
      ],
      recipients: [],
    };

    const { nodes, edges } = workflowToGraph(workflow);

    expect(nodes).toHaveLength(3);
    const actionNodes = nodes.filter((n) => n.type === 'actionNode');
    expect(actionNodes).toHaveLength(2);

    // Verify distinct horizontal positions (branching)
    expect(actionNodes[0].position.x).not.toEqual(actionNodes[1].position.x);
    expect(actionNodes[0].position.y).toEqual(actionNodes[1].position.y);

    // Verify trigger connects to both actions
    expect(edges).toHaveLength(2);
    expect(edges.filter((e) => e.source === 'trigger')).toHaveLength(2);
  });

  it('5. Recipients are represented when present', () => {
    const workflow: GeneratedWorkflow = {
      id: 'wf_5',
      name: 'Workflow with Recipients',
      status: 'ready',
      schema_version: 1,
      intent: { summary: 'Notify on-call engineers' },
      trigger: {
        kind: 'system.failure',
      },
      conditions: [],
      actions: [
        {
          id: 'act_notify',
          kind: 'pagerduty.notify',
          needs_recipients: true,
          parameters: {},
        },
      ],
      recipients: [
        {
          id: 'rcpt_primary',
          channel: 'sms',
          address: '+15551234567',
        },
        {
          id: 'rcpt_secondary',
          channel: 'email',
          address: 'oncall@example.com',
        },
      ],
    };

    const { nodes, edges } = workflowToGraph(workflow);

    expect(nodes).toHaveLength(4);
    const recipientNodes = nodes.filter((n) => n.type === 'recipientNode');
    expect(recipientNodes).toHaveLength(2);

    // Action connects to both recipients
    const toRecipients = edges.filter((e) => e.source === 'action-act_notify');
    expect(toRecipients).toHaveLength(2);
    expect(toRecipients.map((e) => e.target)).toEqual([
      'recipient-rcpt_primary',
      'recipient-rcpt_secondary',
    ]);
  });

  it('6. Optional condition does not create an empty condition node when empty', () => {
    const workflow: GeneratedWorkflow = {
      id: 'wf_6',
      name: 'No Conditions Workflow',
      status: 'ready',
      schema_version: 1,
      intent: { summary: 'Direct trigger to action' },
      trigger: {
        kind: 'timer.tick',
      },
      conditions: [],
      actions: [
        {
          id: 'act_sync',
          kind: 'data.sync',
          parameters: {},
        },
      ],
      recipients: [],
    };

    const { nodes } = workflowToGraph(workflow);

    // Must not contain any conditionNode
    const conditionNodes = nodes.filter((n) => n.type === 'conditionNode');
    expect(conditionNodes).toHaveLength(0);
  });

  it('7. Missing optional fields do not crash the visualization', () => {
    const sparseWorkflow = {
      id: 'wf_sparse',
      name: 'Sparse Workflow',
      status: 'ready',
      schema_version: 1,
      intent: {},
      trigger: {
        kind: 'custom.event',
      },
      conditions: [{ expression: null }], // expression is null, no id
      actions: [{ kind: null, parameters: {} }], // kind is null, no id
      recipients: [{ channel: null, address: null }], // channel/address null, no id
    } as unknown as GeneratedWorkflow;

    expect(() => {
      const { nodes, edges } = workflowToGraph(sparseWorkflow);
      expect(nodes.length).toBeGreaterThan(0);
      expect(edges.length).toBeGreaterThan(0);
    }).not.toThrow();
  });

  it('8. No generated workflow results in no graph (empty nodes and edges)', () => {
    expect(workflowToGraph(null)).toEqual({ nodes: [], edges: [] });
    expect(workflowToGraph(undefined)).toEqual({ nodes: [], edges: [] });
    expect(
      workflowToGraph({
        id: '',
        name: '',
        status: '',
        schema_version: 1,
        intent: {},
        trigger: { kind: null },
        conditions: [],
        actions: [],
        recipients: [],
      })
    ).toEqual({ nodes: [], edges: [] });
  });
});
