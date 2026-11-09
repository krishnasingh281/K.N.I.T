/**
 * ChatWindow — scrollable message list with streaming support.
 * Consumes useChat hook; renders ChatMessage + ChatInput.
 * Props: socket (Socket.io instance)
 */
import { useEffect, useRef } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useChat } from '../hooks/useChat';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';

export const ChatWindow = ({ socket }) => {
  const { messages, isGenerating, error, sendMessage } = useChat(socket);
  const listRef = useRef(null);

  // Auto-scroll on new messages / streaming tokens
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <div className="flex flex-col h-[calc(100vh)]">

      {/* Scrollable messages */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto px-10 py-8 flex flex-col gap-5"
        aria-label="Chat messages"
        role="log"
        aria-live="polite"
        aria-atomic="false"
      >
        {messages.length > 0 && (
          <AnimatePresence initial={false}>
            {messages.map((msg, idx) => (
              <ChatMessage
                key={idx}
                message={msg}
                isCurrentlyStreaming={
                  isGenerating && idx === messages.length - 1
                }
              />
            ))}
          </AnimatePresence>
        )}

        {/* Error banner */}
        {error && (
          <div className="text-sm text-[var(--danger)] border border-[rgba(248,113,113,0.3)] bg-[rgba(248,113,113,0.08)] rounded-lg px-4 py-3">
            {error}
          </div>
        )}
      </div>

      {/* Fixed input bar */}
      <ChatInput onSend={sendMessage} disabled={isGenerating || !socket} />
    </div>
  );
};
