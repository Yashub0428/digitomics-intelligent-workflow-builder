import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface MessageInputProps {
  onSend: (content: string) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  isLoading,
  disabled = false,
  placeholder = 'Type your message or automation request...',
}) => {
  const [content, setContent] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed || isLoading || disabled) return;

    onSend(trimmed);
    setContent('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    // Auto-adjust height up to 120px
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        120
      )}px`;
    }
  };

  const isBlank = !content.trim();

  return (
    <div className="bg-white border-t border-slate-200 p-3 sm:p-4">
      <form onSubmit={handleSubmit} className="relative flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          className="w-full resize-none rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 max-h-32 transition-colors"
        />

        <button
          type="submit"
          disabled={isBlank || isLoading || disabled}
          className="h-11 w-11 shrink-0 rounded-xl bg-indigo-600 flex items-center justify-center text-white hover:bg-indigo-700 disabled:bg-slate-200 disabled:text-slate-400 transition-colors shadow-xs cursor-pointer disabled:cursor-not-allowed"
          title="Send message (Enter)"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-4 h-4 ml-0.5" />
          )}
        </button>
      </form>
      <div className="flex justify-between items-center mt-1.5 px-1 text-[11px] text-slate-400">
        <span>Press <kbd className="px-1 py-0.5 rounded bg-slate-100 border text-slate-500 font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-slate-100 border text-slate-500 font-mono text-[10px]">Shift+Enter</kbd> for new line</span>
        {content.length > 0 && <span>{content.length} chars</span>}
      </div>
    </div>
  );
};
