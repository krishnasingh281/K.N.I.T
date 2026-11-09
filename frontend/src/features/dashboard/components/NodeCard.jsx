/**
 * NodeCard — displays a single cluster node's telemetry.
 *
 * Props:
 *   node: {
 *     id: string,
 *     gpu: string,
 *     vram?: string,          // legacy string field (e.g. "24 GB") — OR use vramUsed/vramTotal
 *     vramUsed?: number,      // GB
 *     vramTotal?: number,     // GB
 *     layerStart?: number,
 *     layerEnd?: number,
 *     status: 'active' | 'healthy' | 'dead',
 *     joinedAt?: string | number,
 *     lastSeen?: string | number,
 *   }
 *   assignment?: { startLayer, endLayer, orderIndex }
 */
import { motion } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import { cardVariants } from '../../../shared/lib/motion';
import { cn } from '../../../shared/lib/cn';
import { StatusDot } from './StatusDot';

export const NodeCard = ({ node, assignment }) => {
  const isDead = node.status === 'dead';
  const isActive = !isDead;

  // Support both vramUsed/vramTotal (numeric) and legacy vram (string)
  const hasNumericVram = typeof node.vramUsed === 'number' && typeof node.vramTotal === 'number';
  const vramPct = hasNumericVram && node.vramTotal > 0
    ? (node.vramUsed / node.vramTotal) * 100
    : 0;
  const barColor = vramPct >= 90 ? '#F87171' : '#4C8DFF';

  // Layer range — prefer assignment over node fields
  const layerStart = assignment?.startLayer ?? node.layerStart;
  const layerEnd   = assignment?.endLayer   ?? node.layerEnd;
  const hasLayers  = layerStart != null && layerEnd != null;

  return (
    <motion.article
      variants={cardVariants}
      className={cn('knit-card p-5 flex flex-col gap-3', isDead && 'opacity-70')}
      style={isDead ? { borderColor: 'rgba(248,113,113,0.35)' } : undefined}
      aria-label={`Node ${node.id}, status: ${node.status}`}
    >
      {/* Top row: ID + status */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-sm font-medium text-[var(--text)]">{node.id}</span>
        <StatusDot status={node.status} />
      </div>

      {/* GPU */}
      <span className="text-[13px] text-[var(--text-muted)]">{node.gpu}</span>

      {/* VRAM string (legacy) */}
      {!hasNumericVram && node.vram && (
        <span className="font-mono text-xs text-[var(--text-faint)]">
          VRAM: {node.vram}
        </span>
      )}

      {/* Layer range */}
      {hasLayers ? (
        <span className="font-mono text-xs text-[var(--text-faint)]">
          Layers {layerStart}–{layerEnd}
          {assignment?.orderIndex != null && (
            <span className="text-[var(--text-faint)]"> · pos {assignment.orderIndex}</span>
          )}
        </span>
      ) : (
        isActive && (
          <span className="font-mono text-xs text-[var(--text-faint)] italic">
            Awaiting assignment…
          </span>
        )
      )}

      {/* Dead node warning */}
      {isDead && (
        <span className="flex items-center gap-1.5 text-xs text-[var(--danger)]">
          <AlertTriangle size={12} aria-hidden="true" />
          Node offline
        </span>
      )}

      {/* VRAM progress bar (numeric) */}
      {hasNumericVram && (
        <div className="flex flex-col gap-1.5 mt-auto">
          <span className="font-mono text-xs text-[var(--text-muted)]">
            {node.vramUsed} GB / {node.vramTotal} GB
          </span>
          <div
            className="w-full h-1 rounded-full"
            style={{ backgroundColor: 'var(--border)' }}
            role="meter"
            aria-label={`VRAM usage ${Math.round(vramPct)}%`}
            aria-valuenow={Math.round(vramPct)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${vramPct}%`, backgroundColor: barColor }}
            />
          </div>
        </div>
      )}

      {/* Join/seen times (from real socket data) */}
      {node.joinedAt && (
        <div className="pt-3 border-t border-[var(--border-subtle)] flex justify-between text-[11px] text-[var(--text-faint)]">
          <span>Joined: {new Date(node.joinedAt).toLocaleTimeString()}</span>
          {node.lastSeen && (
            <span>Seen: {new Date(node.lastSeen).getSeconds()}s ago</span>
          )}
        </div>
      )}
    </motion.article>
  );
};

