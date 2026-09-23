import React from 'react';
import { User, Sparkles } from 'lucide-react';
import type { ConversationMessage } from '../../types/conversation';


interface MessageBubbleProps {
  message: ConversationMessage;
  onSelectOption?: (option: string) => void;
  options?: string[];
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onSelectOption,
  options,
}) => {
  const isUser = message.role === 'user';

  const formatTime = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div
      className={`flex items-start gap-3 my-3.5 ${
        isUser ? 'flex-row-reverse' : 'flex-row'
      }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-xs ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-indigo-600 text-white'
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-xs ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-xs'
            : 'bg-white border border-slate-200 text-slate-800 rounded-tl-xs'
        }`}
      >
        <div className="text-sm leading-relaxed whitespace-pre-wrap font-normal">
          {message.content}
        </div>

        {/* Ambiguity Quick Choices (if options provided on this turn) */}
        {!isUser && options && options.length > 0 && onSelectOption && (
          <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap gap-1.5">
            <span className="text-[11px] font-medium text-slate-400 w-full mb-1">
              Suggested choices:
            </span>
            {options.map((opt, i) => (
              <button
                key={i}
                onClick={() => onSelectOption(opt)}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition-colors cursor-pointer"
              >
                {opt}
              </button>
            ))}
          </div>
        )}

        <div
          className={`text-[10px] mt-1 text-right ${
            isUser ? 'text-blue-200' : 'text-slate-400'
          }`}
        >
          {formatTime(message.created_at)}
        </div>
      </div>
    </div>
  );
};
