import React from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { UserCheck } from 'lucide-react';
import type { RecipientNodeData } from '../workflowToGraph';

export const RecipientNode: React.FC<NodeProps<Node<RecipientNodeData>>> = ({ data }) => {
  const { channel, address } = data;

  return (
    <div className="w-64 rounded-xl border border-purple-200 bg-white shadow-xs hover:shadow-md transition-shadow text-left select-none overflow-hidden">
      {/* Upstream Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-purple-500 border-2 border-white ring-2 ring-purple-200"
      />

      {/* Node Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-purple-50/80 border-b border-purple-100">
        <div className="p-1 rounded bg-purple-100 text-purple-600">
          <UserCheck className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs font-bold text-purple-900 tracking-wide uppercase">
          Recipient
        </span>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2 text-xs">
        <div>
          <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">
            Target / Address
          </span>
          <div className="font-semibold text-purple-950 text-[11px] truncate bg-purple-50/70 p-1.5 rounded border border-purple-100">
            {address || 'Not specified'}
          </div>
        </div>

        {channel && (
          <div className="flex items-center justify-between text-[11px] pt-1 border-t border-slate-100">
            <span className="text-slate-500">Channel:</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px]">
              {channel}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
