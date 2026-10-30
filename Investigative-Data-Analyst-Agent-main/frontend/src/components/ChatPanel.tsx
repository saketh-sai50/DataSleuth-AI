import React, { useState, useRef, useEffect } from 'react';

export interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  actions?: string[];
}

interface ChatPanelProps {
  messages: ChatMessage[];
  onSendMessage: (msg: string) => void;
  isLoading: boolean;
  onActionClick?: (action: string) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onActionClick,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleAction = (action: string) => {
    if (onActionClick) {
      onActionClick(action);
    } else {
      onSendMessage(action);
    }
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl flex flex-col h-[500px]">
      {/* Header */}
      <div className="p-4 border-b border-[#2a2d3e] flex items-center space-x-3 bg-[#1e212d] rounded-t-xl">
        <div className="h-2.5 w-2.5 rounded-full bg-[#10b981] animate-pulse"></div>
        <div>
          <h2 className="text-sm font-semibold text-white">Investigative Chat Assistant</h2>
          <p className="text-[10px] text-[#94a3b8]">Ask follow-up questions and inspect evidence</p>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-3">
            <div className="bg-[#2a2d3e] p-3 rounded-full text-[#6366f1]">
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <p className="text-sm text-[#e2e8f0] font-medium">Start an Investigation</p>
            <p className="text-xs text-[#64748b] max-w-xs">
              Upload datasets on the left, select them, and ask a question to begin a deep analytical investigation.
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg p-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-[#6366f1] text-white rounded-br-none'
                    : 'bg-[#2a2d3e]/50 border border-[#2a2d3e] text-[#e2e8f0] rounded-bl-none'
                }`}
              >
                {msg.content}
              </div>

              {/* Action Chips */}
              {msg.role === 'ai' && msg.actions && msg.actions.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {msg.actions.map((act, actIdx) => (
                    <button
                      key={actIdx}
                      onClick={() => handleAction(act)}
                      className="text-[11px] bg-[#1f2230] border border-[#2a2d3e] hover:border-[#6366f1]/50 text-[#6366f1] px-2.5 py-1 rounded-full transition-all duration-200"
                    >
                      {act}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start space-x-2">
            <div className="bg-[#2a2d3e]/50 border border-[#2a2d3e] text-[#e2e8f0] rounded-lg rounded-bl-none p-3 text-sm">
              <div className="flex space-x-1 items-center h-4">
                <div className="h-1.5 w-1.5 bg-[#94a3b8] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="h-1.5 w-1.5 bg-[#94a3b8] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="h-1.5 w-1.5 bg-[#94a3b8] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-[#2a2d3e] bg-[#1e212d] rounded-b-xl flex space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question or request detail..."
          disabled={isLoading}
          className="flex-1 bg-[#141620] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#6366f1] placeholder-[#64748b] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="bg-[#6366f1] hover:bg-[#4f46e5] disabled:bg-[#6366f1]/50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  );
};
