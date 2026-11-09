/**
 * ChatMessage — single message bubble in the thread.
 * Props: message { role: 'user'|'ai', content: string, isStreaming?: boolean }
 */
import { motion } from 'framer-motion';
import { messageVariants } from '../../../shared/lib/motion';
import { cn } from '../../../shared/lib/cn';

export const ChatMessage = ({ message, isCurrentlyStreaming }) => {
  const isUser = message.role === 'user';
  const isStreamingThis = isCurrentlyStreaming && message.role === 'ai';

  return (
    <motion.div
      variants={messageVariants}
      initial="initial"
      animate="animate"
      className={cn('flex', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'flex flex-col gap-1',
          isUser ? 'items-end max-w-[60%]' : 'items-start w-full max-w-[80%]'
        )}
      >
        {/* Model label */}
        {!isUser && (
          <span className="font-mono text-[11px] text-[var(--text-faint)] px-1">
            knit
          </span>
        )}

        <div
          className={cn(
            'rounded-[10px] px-4 py-3 text-sm leading-relaxed text-[var(--text)]',
            isUser
              ? 'bg-[var(--surface)] border border-[var(--border)]'
              : 'bg-[var(--surface-raised)] border border-[var(--border)]'
          )}
          aria-live={isStreamingThis ? 'polite' : undefined}
          aria-atomic={isStreamingThis ? 'false' : undefined}
        >
          {message.content}
          {/* Blinking caret while this message is streaming */}
          {isStreamingThis && (
            <motion.span
              className="inline-block w-px h-[1em] ml-0.5 align-middle"
              style={{ backgroundColor: '#4C8DFF' }}
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.6, repeat: Infinity, ease: 'linear' }}
              aria-hidden="true"
            />
          )}
        </div>
      </div>
    </motion.div>
  );
};

