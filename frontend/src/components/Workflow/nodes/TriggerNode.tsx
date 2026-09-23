import React from 'react';
import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { Zap, Clock, Box } from 'lucide-react';
import type { TriggerNodeData } from '../workflowToGraph';

export const TriggerNode: React.FC<NodeProps<Node<TriggerNodeData>>> = ({ data }) => {
  const { kind, source, schedule } = data;

  return (
    <div className="w-64 rounded-xl border border-indigo-200 bg-white shadow-xs hover:shadow-md transition-shadow text-left select-none overflow-hidden">
      {/* Node Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-indigo-50/80 border-b border-indigo-100">
        <div className="p-1 rounded bg-indigo-100 text-indigo-600">
          <Zap className="w-3.5 h-3.5" />
        </div>
        <span className="text-xs font-bold text-indigo-900 tracking-wide uppercase">
          Trigger
        </span>
      </div>

      {/* Node Content */}
      <div className="p-3 space-y-2 text-xs">
        <div>
          <span className="text-[10px] uppercase font-semibold text-slate-400 block mb-0.5">
            Event / Kind
          </span>
          <span className="inline-block px-2 py-0.5 rounded font-mono font-semibold text-indigo-950 bg-indigo-50 border border-indigo-100/80 text-[11px] break-all">
            {kind || 'Not specified'}
          </span>
        </div>

        {source && (source.kind || source.identifier) && (
          <div className="flex items-center gap-1.5 text-slate-600 text-[11px] pt-1 border-t border-slate-100">
            <Box className="w-3 h-3 text-slate-400 shrink-0" />
            <span className="truncate">
              Source: <strong className="font-medium text-slate-800">{source.kind || source.identifier}</strong>
              {source.kind && source.identifier ? ` (${source.identifier})` : ''}
            </span>
          </div>
        )}

        {schedule && (schedule.frequency || schedule.cron) && (
          <div className="flex items-center gap-1.5 text-blue-700 text-[11px] pt-1 border-t border-slate-100">
            <Clock className="w-3 h-3 text-blue-500 shrink-0" />
            <span className="truncate">
              Schedule: <strong className="font-medium">{schedule.frequency || schedule.cron}</strong>
              {schedule.timezone ? ` (${schedule.timezone})` : ''}
            </span>
          </div>
        )}
      </div>

      {/* Downstream Connection Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2.5 h-2.5 bg-indigo-500 border-2 border-white ring-2 ring-indigo-200"
      />
    </div>
  );
};
