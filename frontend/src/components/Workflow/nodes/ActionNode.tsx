import React from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Play } from 'lucide-react';
import type { ActionNodeData } from '../workflowToGraph';

export const ActionNode: React.FC<NodeProps<Node<ActionNodeData>>> = ({ data }) => {
  const { kind, parameters, needs_recipients } = data;
  const paramEntries = Object.entries(parameters || {});

  return (
    <div className="w-64 rounded-xl border border-emerald-200 bg-white shadow-xs hover:shadow-md transition-shadow text-left select-none overflow-hidden">
      {/* Upstream Connection Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-2.5 h-2.5 bg-emerald-500 border-2 border-white ring-2 ring-emerald-200"
      />

      {/* Node Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-emerald-50/80 border-b border-emerald-100">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-emerald-100 text-emerald-600">
            <Play className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-emerald-900 tracking-wide uppercase">
            Action
          </span>
        </div>
        {needs_recipients && (
          <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[9px] font-semibold">
            Needs Recipient
          </span>
        )}
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2 text-xs">
        <div>
          <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">
            Action Kind
          </span>
          <span className="inline-block px-2 py-0.5 rounded font-mono font-semibold text-emerald-950 bg-emerald-50 border border-emerald-100/80 text-[11px] break-all">
            {kind || 'Not specified'}
          </span>
        </div>

        {paramEntries.length > 0 && (
          <div className="pt-1.5 border-t border-slate-100">
            <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">
              Parameters
            </span>
            <div className="space-y-1 bg-slate-50 p-2 rounded border border-slate-100 text-[11px] font-mono text-slate-700">
              {paramEntries.map(([key, val]) => (
                <div key={key} className="truncate">
                  <span className="text-slate-400 font-sans">{key}: </span>
                  <span className="text-slate-900 font-medium">
                    {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Downstream Connection Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-emerald-500 border-2 border-white ring-2 ring-emerald-200"
      />
    </div>
  );
};
