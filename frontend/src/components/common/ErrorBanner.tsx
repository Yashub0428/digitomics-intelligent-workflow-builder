import React from 'react';
import { AlertCircle, X } from 'lucide-react';

interface ErrorBannerProps {
  message: string | null;
  onDismiss: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss }) => {
  if (!message) return null;

  return (
    <div className="bg-rose-50 border-b border-rose-200 px-4 py-2.5 flex items-center justify-between text-xs text-rose-800">
      <div className="flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
        <span>{message}</span>
      </div>
      <button
        onClick={onDismiss}
        className="p-1 rounded hover:bg-rose-100 text-rose-600 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
