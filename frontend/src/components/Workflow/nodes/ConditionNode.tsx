import React from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Sliders } from 'lucide-react';
import type { ConditionNodeData } from '../workflowToGraph';

export const ConditionNode: React.FC<NodeProps<Node<ConditionNodeData>>> = ({ data }) => {
  const { expression } = data;

  return (
    <div className="w-64 rounded-xl border border-amber-200 bg-white shadow-xs hover:shadow-md transition-shadow text-left select-none overflow-hidden">
      {/* Upstream Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-amber-500 border-2 border-white ring-2 ring-amber-200"
      />

      {/* Node Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-amber-50/80 border-b border-amber-100">
        <div className="p-1 rounded bg-amber-100 text-amber-600">
          <Sliders className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs font-bold text-amber-900 tracking-wide uppercase">
          Condition
        </span>
      </div>

      {/* Node Content */}
      <div className="p-3 text-xs">
        <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">
          Rule / Expression
        </span>
        <div className="font-mono text-[11px] p-2 rounded bg-amber-50/70 border border-amber-100 text-amber-950 font-medium break-words leading-relaxed">
          {expression || 'Not specified'}
        </div>
      </div>

      {/* Downstream Connection Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-amber-500 border-2 border-white ring-2 ring-amber-200"
      />
    </div>
  );
};
