import React, { useState } from 'react';
import {
  X,
  Check,
  Copy,
  Download,
  CheckCircle2,
  FileCode,
  Network,
} from 'lucide-react';
import type { GeneratedWorkflow } from '../../types/workflow';
import { WorkflowGraph } from './WorkflowGraph';

interface WorkflowModalProps {
  workflow: GeneratedWorkflow | null;
  isOpen: boolean;
  onClose: () => void;
}

export const WorkflowModal: React.FC<WorkflowModalProps> = ({
  workflow,
  isOpen,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'visual' | 'json'>('visual');
  const [copied, setCopied] = useState(false);

  if (!isOpen || !workflow) return null;

  const jsonString = JSON.stringify(workflow, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-${workflow.id || 'export'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-5xl w-full h-[90vh] flex flex-col overflow-hidden animate-in fade-in duration-200">
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Workflow Specification Generated
              </h3>
              <p className="text-xs text-slate-500">
                Read-only structured workflow definition and interactive diagram
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
            title="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Workflow Overview Banner */}
        <div className="px-5 py-2.5 bg-emerald-50/50 border-b border-emerald-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div>
            <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
              Workflow Name
            </span>
            <div className="text-sm font-bold text-emerald-950">
              {workflow.name}
            </div>
          </div>

          <div className="flex items-center gap-4 text-slate-600 text-[11px]">
            <div>
              <span className="text-slate-400 block text-[10px]">ID</span>
              <span className="font-mono font-medium text-slate-800">{workflow.id}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Trigger</span>
              <span className="font-medium text-slate-800">{workflow.trigger?.kind || 'N/A'}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Conditions</span>
              <span className="font-medium text-slate-800">{workflow.conditions?.length || 0}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Actions</span>
              <span className="font-medium text-slate-800">{workflow.actions?.length || 0}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">Recipients</span>
              <span className="font-medium text-slate-800">{workflow.recipients?.length || 0}</span>
            </div>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="px-5 pt-3 pb-2 border-b border-slate-200 bg-white flex items-center justify-between">
          <div className="inline-flex p-1 bg-slate-100 rounded-lg text-xs font-medium">
            <button
              onClick={() => setActiveTab('visual')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                activeTab === 'visual'
                  ? 'bg-white text-indigo-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <span>Visual</span>
            </button>
            <button
              onClick={() => setActiveTab('json')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                activeTab === 'json'
                  ? 'bg-white text-indigo-700 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>JSON</span>
            </button>
          </div>

          {activeTab === 'json' && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
              <button
                onClick={handleDownload}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download</span>
              </button>
            </div>
          )}
        </div>

        {/* Modal Main Content */}
        <div className="flex-1 overflow-hidden p-4 bg-slate-50/50 flex flex-col">
          {activeTab === 'visual' ? (
            <div className="flex-1 w-full h-full min-h-0">
              <WorkflowGraph workflow={workflow} />
            </div>
          ) : (
            <div className="flex-1 w-full h-full min-h-0 relative rounded-xl border border-slate-200 bg-slate-900 overflow-hidden flex flex-col shadow-inner">
              <pre className="flex-1 p-4 text-slate-200 font-mono text-[11px] overflow-auto leading-relaxed select-text">
                {jsonString}
              </pre>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
          <span className="italic">
            {activeTab === 'visual'
              ? 'Read-only graph visualization. Use controls to zoom, pan, and fit.'
              : 'Read-only JSON representation directly generated by backend.'}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 text-white text-xs font-semibold hover:bg-slate-900 transition-colors shadow-xs cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
