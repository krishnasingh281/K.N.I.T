/**
 * ChatInput — textarea + send button.
 * Props: onSend (fn), disabled (bool)
 */
import { useRef, useState } from 'react';
import { Send } from 'lucide-react';
import { cn } from '../../../shared/lib/cn';

export const ChatInput = ({ onSend, disabled = false }) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleInput = (e) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <div
      className={cn(
        'flex items-end gap-3 px-10 py-5',
        'border-t border-[var(--border)] bg-[var(--bg)]',
        disabled && 'opacity-60'
      )}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        placeholder="Send a message…"
        className={cn(
          'flex-1 resize-none rounded-lg px-4 py-3',
          'bg-[var(--surface)] border border-[var(--border)]',
          'text-sm text-[var(--text)] placeholder:text-[var(--text-faint)]',
          'focus:outline-none focus:border-[var(--accent)]',
          'transition-colors duration-150',
          'min-h-[44px] max-h-[200px] leading-relaxed',
          disabled && 'cursor-not-allowed'
        )}
        aria-label="Message input"
        aria-disabled={disabled}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className={cn(
          'flex-shrink-0 flex items-center justify-center',
          'w-10 h-10 rounded-lg',
          'bg-[var(--accent)] text-white',
          'hover:brightness-110 active:brightness-90',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]',
          'transition-all duration-150',
          'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:brightness-100'
        )}
        aria-label="Send message"
      >
        <Send size={16} aria-hidden="true" />
      </button>
    </div>
  );
};

