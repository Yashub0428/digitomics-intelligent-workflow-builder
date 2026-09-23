import React from 'react';
import { Bot, ArrowRight, Zap, Clock, ShieldAlert } from 'lucide-react';

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onSelectPrompt }) => {
  const suggestions = [
    {
      title: 'Invoice Notification',
      prompt: 'When I receive a new invoice, notify the finance team.',
      icon: <Zap className="w-4 h-4 text-amber-500" />,
    },
    {
      title: 'Daily Digest',
      prompt: 'Every morning, summarize my new emails.',
      icon: <Clock className="w-4 h-4 text-blue-500" />,
    },
    {
      title: 'E-commerce Alert',
      prompt: 'When a high-value order is created, notify Slack.',
      icon: <ShieldAlert className="w-4 h-4 text-emerald-500" />,
    },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-xl mx-auto">
      <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-4 shadow-xs">
        <Bot className="w-7 h-7" />
      </div>

      <h2 className="text-xl font-bold text-slate-800 mb-2">
        Describe the automation you want to build
      </h2>
      <p className="text-sm text-slate-500 mb-8 leading-relaxed">
        The assistant will extract your intent, identify triggers and actions, and ask focused questions for any missing details without making unstated assumptions.
      </p>

      <div className="w-full space-y-2.5 text-left">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
          Example prompts to get started:
        </span>
        {suggestions.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectPrompt(item.prompt)}
            className="w-full flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-xs hover:bg-slate-50 transition-all group"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-slate-100 group-hover:bg-indigo-50 transition-colors">
                {item.icon}
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-700 block">
                  {item.title}
                </span>
                <span className="text-xs text-slate-500 font-normal">
                  "{item.prompt}"
                </span>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition-colors" />
          </button>
        ))}
      </div>
    </div>
  );
};
