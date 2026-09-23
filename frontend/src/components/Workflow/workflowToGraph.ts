import type { Node, Edge } from '@xyflow/react';
import { MarkerType } from '@xyflow/react';
import type { GeneratedWorkflow } from '../../types/workflow';

export interface TriggerNodeData extends Record<string, unknown> {
  kind: string | null;
  source?: {
    kind?: string | null;
    identifier?: string | null;
  } | null;
  schedule?: {
    frequency?: string | null;
    cron?: string | null;
    timezone?: string | null;
  } | null;
}

export interface ConditionNodeData extends Record<string, unknown> {
  id: string;
  expression: string | null;
}

export interface ActionNodeData extends Record<string, unknown> {
  id: string;
  kind: string | null;
  parameters: Record<string, unknown>;
  needs_recipients?: boolean;
}

export interface RecipientNodeData extends Record<string, unknown> {
  id: string;
  channel: string | null;
  address: string | null;
}

/**
 * Computes deterministic centered X positions for a row of items.
 */
function getRowXPositions(
  count: number,
  nodeWidth: number = 240,
  gap: number = 40,
  centerX: number = 250
): number[] {
  if (count <= 0) return [];
  const totalWidth = count * nodeWidth + (count - 1) * gap;
  const startX = centerX - totalWidth / 2;
  return Array.from({ length: count }, (_, i) => startX + i * (nodeWidth + gap));
}

function createEdge(source: string, target: string): Edge {
  return {
    id: `e-${source}-${target}`,
    source,
    target,
    type: 'smoothstep',
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 16,
      height: 16,
      color: '#64748b',
    },
    style: {
      stroke: '#94a3b8',
      strokeWidth: 2,
    },
    animated: true,
  };
}

/**
 * Converts a backend-generated workflow into React Flow nodes and edges.
 * Strictly read-only, deterministic, and creates only nodes present in the response.
 */
export function workflowToGraph(
  workflow: GeneratedWorkflow | null | undefined
): { nodes: Node[]; edges: Edge[] } {
  if (!workflow || !workflow.trigger || !workflow.trigger.kind) {
    return { nodes: [], edges: [] };
  }

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const triggerNodeId = 'trigger';
  const conditions = workflow.conditions || [];
  const actions = workflow.actions || [];
  const recipients = workflow.recipients || [];

  const hasConditions = conditions.length > 0;
  const hasActions = actions.length > 0;
  const hasRecipients = recipients.length > 0;

  // 1. Level 0: Trigger Node
  const triggerX = 250 - 120; // centered at 250
  const triggerY = 40;

  nodes.push({
    id: triggerNodeId,
    type: 'triggerNode',
    position: { x: triggerX, y: triggerY },
    data: {
      kind: workflow.trigger.kind,
      source: (workflow.trigger.source as TriggerNodeData['source']) || null,
      schedule: (workflow.trigger.schedule as TriggerNodeData['schedule']) || null,
    } satisfies TriggerNodeData,
  });

  // 2. Level 1: Condition Nodes (if any)
  const conditionNodeIds: string[] = [];
  let nextY = 180;

  if (hasConditions) {
    const condXPositions = getRowXPositions(conditions.length);
    conditions.forEach((cond, idx) => {
      const condId = (cond.id as string) || `cond_${idx + 1}`;
      const nodeId = `condition-${condId}`;
      conditionNodeIds.push(nodeId);

      nodes.push({
        id: nodeId,
        type: 'conditionNode',
        position: { x: condXPositions[idx], y: nextY },
        data: {
          id: condId,
          expression: (cond.expression as string) || null,
        } satisfies ConditionNodeData,
      });

      // Connect Trigger to each Condition
      edges.push(createEdge(triggerNodeId, nodeId));
    });
    nextY += 140;
  }

  // 3. Level 2: Action Nodes (if any)
  const actionNodeIds: string[] = [];
  const recipientTargetActionIds: string[] = [];

  if (hasActions) {
    const actionXPositions = getRowXPositions(actions.length);
    actions.forEach((act, idx) => {
      const actId = (act.id as string) || `act_${idx + 1}`;
      const nodeId = `action-${actId}`;
      actionNodeIds.push(nodeId);

      const needsRecipients = Boolean(act.needs_recipients);
      if (needsRecipients) {
        recipientTargetActionIds.push(nodeId);
      }

      nodes.push({
        id: nodeId,
        type: 'actionNode',
        position: { x: actionXPositions[idx], y: nextY },
        data: {
          id: actId,
          kind: (act.kind as string) || null,
          parameters: (act.parameters as Record<string, unknown>) || {},
          needs_recipients: needsRecipients,
        } satisfies ActionNodeData,
      });

      // Connect upstream to this Action
      if (hasConditions) {
        // Condition(s) -> Action
        conditionNodeIds.forEach((condNodeId) => {
          edges.push(createEdge(condNodeId, nodeId));
        });
      } else {
        // Trigger -> Action
        edges.push(createEdge(triggerNodeId, nodeId));
      }
    });
    nextY += 140;
  }

  // 4. Level 3: Recipient Nodes (if any)
  if (hasRecipients) {
    const recipientXPositions = getRowXPositions(recipients.length);
    const sourceActionIds =
      recipientTargetActionIds.length > 0 ? recipientTargetActionIds : actionNodeIds;

    recipients.forEach((rcpt, idx) => {
      const rcptId = (rcpt.id as string) || `rcpt_${idx + 1}`;
      const nodeId = `recipient-${rcptId}`;

      nodes.push({
        id: nodeId,
        type: 'recipientNode',
        position: { x: recipientXPositions[idx], y: nextY },
        data: {
          id: rcptId,
          channel: (rcpt.channel as string) || null,
          address: (rcpt.address as string) || (rcpt.identifier as string) || null,
        } satisfies RecipientNodeData,
      });

      // Connect Action(s) -> Recipient
      if (sourceActionIds.length > 0) {
        sourceActionIds.forEach((actNodeId) => {
          edges.push(createEdge(actNodeId, nodeId));
        });
      } else if (!hasActions && !hasConditions) {
        // Fallback: Trigger -> Recipient
        edges.push(createEdge(triggerNodeId, nodeId));
      }
    });
  }

  return { nodes, edges };
}
