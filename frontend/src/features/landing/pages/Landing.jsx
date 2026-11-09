/**
 * Landing page — route: "/"
 * Full-page, no sidebar. Left-aligned asymmetric layout.
 * Contains only: wordmark, headline, supporting line, and one CTA.
 */
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { heroVariants, heroItemVariants } from '../../../shared/lib/motion';

/** Faint animated dot-grid — single restrained ambient background element */
function DotGrid() {
  const prefersReduced = useReducedMotion();

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="dot-grid" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="#1B2536" />
          </pattern>
        </defs>
        <motion.rect
          width="100%"
          height="100%"
          fill="url(#dot-grid)"
          initial={{ opacity: 0 }}
          animate={prefersReduced ? { opacity: 0.4 } : { opacity: [0.3, 0.5, 0.3] }}
          transition={prefersReduced ? { duration: 0.3 } : { duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
      </svg>
    </div>
  );
}

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="relative min-h-screen bg-[var(--bg)] flex flex-col">
      <DotGrid />

      {/* Wordmark */}
      <header className="relative z-10 p-8 md:p-12">
        <span className="font-mono text-sm text-[var(--text-faint)] tracking-tight">
          knit
        </span>
      </header>

      {/* Hero — left-aligned, vertically centered */}
      <main
        className="relative z-10 flex-1 flex items-center px-8 md:px-16 lg:px-24"
        style={{ paddingBottom: '10vh' }}
      >
        <motion.div
          className="max-w-2xl"
          variants={heroVariants}
          initial="initial"
          animate="animate"
        >
          <motion.h1
            variants={heroItemVariants}
            className="text-[clamp(2.5rem,6vw,4rem)] font-semibold leading-[1.1] tracking-tight text-[var(--text)] mb-6"
          >
            Split the model.
            <br />
            Share the work.
          </motion.h1>

          <motion.p
            variants={heroItemVariants}
            className="text-base md:text-lg text-[var(--text-muted)] leading-relaxed mb-10 max-w-xl"
          >
            Run massive language models by distributing inference layers across
            machines on your local network. Fault-tolerant by design.
          </motion.p>

          <motion.div variants={heroItemVariants}>
            <button
              onClick={() => navigate('/dashboard')}
              className={[
                'inline-flex items-center gap-2',
                'bg-[var(--accent)] text-white text-sm font-medium',
                'px-5 py-2.5 rounded-lg',
                'hover:brightness-110 active:brightness-90',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]',
                'transition-all duration-150',
              ].join(' ')}
            >
              Open Dashboard
              <ArrowRight size={16} aria-hidden="true" />
            </button>
          </motion.div>
        </motion.div>
      </main>
    </div>
  );
};

export default Landing;

