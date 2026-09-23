import React from 'react';
import { PlusCircle, Sparkles, FileCode } from 'lucide-react';
import type { ConversationStatus } from '../types/workflow';


interface HeaderProps {
  status?: ConversationStatus;
  onNewWorkflow: () => void;
  onViewWorkflow?: () => void;
  hasWorkflow?: boolean;
  isLoading?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  status = 'COLLECTING',
  onNewWorkflow,
  onViewWorkflow,
  hasWorkflow = false,
  isLoading = false,
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case 'GENERATED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            GENERATED
          </span>
        );
      case 'READY':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-300">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            READY
          </span>
        );
      case 'COLLECTING':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            COLLECTING
          </span>
        );
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-xs">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">
                Intelligent Workflow Builder
              </h1>
              {getStatusBadge()}
            </div>
            <p className="text-xs text-slate-500">
              Build automations through conversation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {hasWorkflow && onViewWorkflow && (
            <button
              onClick={onViewWorkflow}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium bg-emerald-50 text-emerald-700 border border-emerald-300 hover:bg-emerald-100 transition-colors shadow-xs"
            >
              <FileCode className="w-4 h-4" />
              View Workflow
            </button>
          )}

          <button
            onClick={onNewWorkflow}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-xs disabled:opacity-50"
          >
            <PlusCircle className="w-4 h-4" />
            New Workflow
          </button>
        </div>
      </div>
    </header>
  );
};
