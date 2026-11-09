/**
 * Shared Framer Motion variants and transitions for Knit.
 * Durations: 150-400ms. No bounce/spring except sidebar indicator.
 */

/** Page-level fade + y-translate (AnimatePresence) */
export const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -6 },
};

export const pageTransition = {
  duration: 0.22,
  ease: [0.16, 1, 0.3, 1],
};

/** Staggered container for card lists */
export const listVariants = {
  animate: {
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
};

/** Individual card in a staggered list */
export const cardVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.28, ease: 'easeOut' } },
};

/** Sidebar nav active indicator — small tasteful spring */
export const indicatorTransition = {
  type: 'spring',
  stiffness: 380,
  damping: 32,
  mass: 0.8,
};

/** Staggered landing hero */
export const heroVariants = {
  animate: {
    transition: { staggerChildren: 0.1, delayChildren: 0.05 },
  },
};

export const heroItemVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] } },
};

/** Chat message slide-in */
export const messageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
};

