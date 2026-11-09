/**
 * Sidebar — fixed left navigation for the main app layout.
 * Collapses to icon-only rail on small screens (< md breakpoint).
 */
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { indicatorTransition } from './lib/motion';
import { cn } from './lib/cn';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/chat',      label: 'Chat',       Icon: MessageSquare },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <nav
      className={cn(
        'fixed top-0 left-0 h-full z-20',
        'w-14 md:w-[240px]',
        'flex flex-col',
        'bg-[var(--bg)] border-r border-[var(--border)]',
      )}
      aria-label="Primary navigation"
    >
      {/* Wordmark */}
      <div className="flex items-center h-14 px-4 md:px-5 border-b border-[var(--border-subtle)] flex-shrink-0">
        <span className="font-mono text-sm text-[var(--text-faint)] tracking-tight select-none">
          knit
        </span>
      </div>

      {/* Nav links */}
      <ul className="flex flex-col gap-1 p-2 mt-2 flex-1" role="list">
        {NAV_ITEMS.map(({ to, label, Icon }) => {
          const isActive = location.pathname === to || location.pathname.startsWith(to + '/');

          return (
            <li key={to} className="relative">
              {/* Animated active background */}
              <AnimatePresence>
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active-bg"
                    className="absolute inset-0 rounded-lg"
                    style={{ backgroundColor: 'rgba(76,141,255,0.12)' }}
                    transition={indicatorTransition}
                  />
                )}
              </AnimatePresence>

              <NavLink
                to={to}
                className={cn(
                  'relative flex items-center gap-3 rounded-lg px-3 h-10',
                  'text-sm font-medium transition-colors duration-150',
                  'hover:bg-[rgba(76,141,255,0.06)]',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg)]',
                  isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'
                )}
                aria-current={isActive ? 'page' : undefined}
                aria-label={label}
              >
                <Icon size={18} className="flex-shrink-0" aria-hidden="true" />
                <span className="hidden md:block">{label}</span>
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

