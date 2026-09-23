import React from 'react';
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Play,
  FileCode,
  Tag,
  Zap,
  Sliders,
  UserCheck,
  Clock,
} from 'lucide-react';
import type { WorkflowState } from '../../types/workflow';

interface WorkflowStatePanelProps {
  state: WorkflowState | null;
  onViewWorkflow: () => void;
}

export const WorkflowStatePanel: React.FC<WorkflowStatePanelProps> = ({
  state,
  onViewWorkflow,
}) => {

  if (!state) {
    return (
      <div className="w-80 lg:w-96 border-l border-slate-200 bg-white p-6 flex items-center justify-center text-slate-400 text-sm">
        No workflow initialized yet.
      </div>
    );
  }

  const {
    status,
    intent,
    trigger,
    trigger_source,
    schedule,
    conditions,
    actions,
    recipients,
    missing_mandatory_fields = [],
    ambiguities = [],
  } = state;

  const hasMissing = missing_mandatory_fields.length > 0;
  const unresolvedAmbiguities = ambiguities.filter((a) => !a.resolved);

  return (
    <aside className="w-80 lg:w-96 border-l border-slate-200 bg-white flex flex-col h-full overflow-hidden shadow-xs">
      {/* Panel Header */}
      <div className="p-4 border-b border-slate-200 bg-slate-50/50">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Workflow Status
          </span>
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              status === 'GENERATED'
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                : status === 'READY'
                ? 'bg-blue-100 text-blue-800 border border-blue-300'
                : 'bg-amber-100 text-amber-800 border border-amber-300'
            }`}
          >
            {status}
          </span>
        </div>

        {status === 'GENERATED' && (
          <button
            onClick={onViewWorkflow}
            className="w-full mt-2 inline-flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors shadow-xs"
          >
            <FileCode className="w-4 h-4" />
            View Generated Workflow
          </button>
        )}
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* Missing Information Alerts */}
        {hasMissing && (
          <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-3">
            <div className="flex items-center gap-1.5 text-amber-800 font-semibold mb-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
              <span>Missing Information ({missing_mandatory_fields.length})</span>
            </div>
            <ul className="space-y-1 pl-5 list-disc text-amber-900/90 text-[11px]">
              {missing_mandatory_fields.map((field, i) => (
                <li key={i}>
                  <strong className="font-semibold">{field.path}:</strong> {field.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Unresolved Ambiguities */}
        {unresolvedAmbiguities.length > 0 && (
          <div className="rounded-xl border border-indigo-200 bg-indigo-50/80 p-3">
            <div className="flex items-center gap-1.5 text-indigo-800 font-semibold mb-2">
              <HelpCircle className="w-4 h-4 shrink-0 text-indigo-600" />
              <span>Ambiguities to Clarify</span>
            </div>
            <ul className="space-y-1.5 text-indigo-900 text-[11px]">
              {unresolvedAmbiguities.map((amb) => (
                <li key={amb.id} className="p-2 rounded bg-white/70 border border-indigo-100">
                  <div className="font-medium text-slate-800 mb-1">{amb.question}</div>
                  {amb.options.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {amb.options.map((opt) => (
                        <span
                          key={opt.id}
                          className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-800 text-[10px]"
                        >
                          {opt.label}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 1. Intent */}
        <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-2xs">
          <div className="flex items-center gap-1.5 font-semibold text-slate-700 mb-1.5">
            <Tag className="w-3.5 h-3.5 text-slate-500" />
            <span>Intent</span>
          </div>
          {intent.summary ? (
            <p className="text-slate-800 text-xs font-medium leading-relaxed bg-slate-50 p-2 rounded border border-slate-100">
              {intent.summary}
            </p>
          ) : (
            <span className="text-slate-400 italic">No intent stated yet</span>
          )}
        </div>

        {/* 2. Trigger */}
        <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              <span>Trigger</span>
            </div>
            {trigger.kind ? (
              <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-0.5">
                <CheckCircle2 className="w-3 h-3" /> Defined
              </span>
            ) : (
              <span className="text-[10px] text-amber-600 font-medium">Pending</span>
            )}
          </div>

          <div className="space-y-1 text-slate-600 bg-slate-50 p-2 rounded border border-slate-100 text-[11px]">
            <div>
              <span className="text-slate-400">Kind: </span>
              <span className="font-mono font-medium text-slate-800">
                {trigger.kind || 'None'}
              </span>
            </div>
            {(trigger_source.kind || trigger_source.identifier) && (
              <div>
                <span className="text-slate-400">Source: </span>
                <span className="font-medium text-slate-800">
                  {trigger_source.kind}
                  {trigger_source.identifier ? ` (${trigger_source.identifier})` : ''}
                </span>
              </div>
            )}
            {schedule && (schedule.frequency || schedule.cron) && (
              <div className="flex items-center gap-1 mt-1 text-blue-700">
                <Clock className="w-3 h-3" />
                <span>
                  Schedule: {schedule.frequency || schedule.cron}{' '}
                  {schedule.timezone ? `(${schedule.timezone})` : ''}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* 3. Conditions */}
        <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Sliders className="w-3.5 h-3.5 text-blue-500" />
              <span>Conditions ({conditions.length})</span>
            </div>
          </div>
          {conditions.length === 0 ? (
            <span className="text-slate-400 italic text-[11px]">No conditions specified</span>
          ) : (
            <ul className="space-y-1">
              {conditions.map((cond, idx) => (
                <li
                  key={cond.id || idx}
                  className="bg-slate-50 p-2 rounded border border-slate-100 font-mono text-[11px] text-slate-800"
                >
                  {cond.expression || 'Empty expression'}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 4. Actions */}
        <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Play className="w-3.5 h-3.5 text-emerald-500" />
              <span>Actions ({actions.length})</span>
            </div>
            {actions.length > 0 ? (
              <span className="text-[10px] text-emerald-600 font-semibold flex items-center gap-0.5">
                <CheckCircle2 className="w-3 h-3" /> {actions.length} step(s)
              </span>
            ) : (
              <span className="text-[10px] text-amber-600 font-medium">Pending</span>
            )}
          </div>

          {actions.length === 0 ? (
            <span className="text-slate-400 italic text-[11px]">No actions defined</span>
          ) : (
            <div className="space-y-2">
              {actions.map((act, i) => (
                <div
                  key={act.id || i}
                  className="bg-slate-50 p-2.5 rounded-lg border border-slate-100 text-[11px]"
                >
                  <div className="font-semibold text-slate-800 flex items-center justify-between">
                    <span>
                      {i + 1}. {act.kind || 'Unknown kind'}
                    </span>
                    {act.needs_recipients && (
                      <span className="px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 text-[9px] font-normal">
                        Needs Recipient
                      </span>
                    )}
                  </div>
                  {Object.keys(act.parameters || {}).length > 0 && (
                    <div className="mt-1 pt-1 border-t border-slate-200/60 font-mono text-[10px] text-slate-600">
                      {JSON.stringify(act.parameters)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 5. Recipients */}
        <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-2xs">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <UserCheck className="w-3.5 h-3.5 text-purple-500" />
              <span>Recipients ({recipients.length})</span>
            </div>
          </div>
          {recipients.length === 0 ? (
            <span className="text-slate-400 italic text-[11px]">No recipients specified</span>
          ) : (
            <div className="space-y-1">
              {recipients.map((rcpt, i) => (
                <div
                  key={rcpt.id || i}
                  className="bg-slate-50 p-2 rounded border border-slate-100 text-[11px] text-slate-800 flex items-center justify-between"
                >
                  <span className="font-medium">{rcpt.address || 'No address'}</span>
                  {rcpt.channel && (
                    <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 text-[10px]">
                      {rcpt.channel}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
