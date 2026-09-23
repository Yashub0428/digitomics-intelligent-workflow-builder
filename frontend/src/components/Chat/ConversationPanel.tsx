import React, { useEffect, useRef } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import type { ConversationMessage } from '../../types/conversation';

import { MessageBubble } from './MessageBubble';
import { MessageInput } from './MessageInput';
import { EmptyState } from './EmptyState';

interface ConversationPanelProps {
  messages: ConversationMessage[];
  isLoading: boolean;
  onSendMessage: (content: string) => void;
  ambiguityOptions?: string[];
  onSelectOption?: (option: string) => void;
}

export const ConversationPanel: React.FC<ConversationPanelProps> = ({
  messages,
  isLoading,
  onSendMessage,
  ambiguityOptions,
  onSelectOption,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-50 overflow-hidden">
      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        {messages.length === 0 ? (
          <EmptyState onSelectPrompt={onSendMessage} />
        ) : (
          <div className="max-w-3xl mx-auto space-y-1">
            {messages.map((msg, index) => {
              const isLastAssistantMsg =
                index === messages.length - 1 && msg.role === 'assistant';

              return (
                <MessageBubble
                  key={msg.id || index}
                  message={msg}
                  options={isLastAssistantMsg ? ambiguityOptions : undefined}
                  onSelectOption={onSelectOption}
                />
              );
            })}

            {/* Thinking / Loading indicator */}
            {isLoading && (
              <div className="flex items-start gap-3 my-3">
                <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white shrink-0 shadow-xs">
                  <Sparkles className="w-4 h-4 animate-spin" />
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs px-4 py-3 shadow-xs flex items-center gap-2 text-slate-500 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                  <span>Analyzing requirements and checking workflow completeness...</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input area */}
      <MessageInput
        onSend={onSendMessage}
        isLoading={isLoading}
        disabled={false}
      />
    </div>
  );
};
