/**
 * StatusDot — per-node heartbeat indicator.
 * Props: status ('healthy' | 'dead'), size (px, default 8)
 */
import { motion, useReducedMotion } from 'framer-motion';

export const StatusDot = ({ status, size = 8 }) => {
  const prefersReduced = useReducedMotion();
  const isHealthy = status === 'healthy' || status === 'active';

  return (
    <span
      className="relative inline-flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size }}
      aria-label={isHealthy ? 'Node healthy' : 'Node offline'}
      role="img"
    >
      {/* Pulse ring — healthy only */}
      {isHealthy && !prefersReduced && (
        <motion.span
          className="absolute inset-0 rounded-full"
          style={{ backgroundColor: '#34D399' }}
          animate={{ scale: [1, 1.9], opacity: [0.5, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'easeOut' }}
        />
      )}
      {/* Core dot */}
      <span
        className="rounded-full block"
        style={{
          width: size,
          height: size,
          backgroundColor: isHealthy ? '#34D399' : '#F87171',
        }}
      />
    </span>
  );
};

