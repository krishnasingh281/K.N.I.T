/**
 * MainLayout — shell for all app routes with sidebar.
 * AnimatePresence wraps <Outlet/> for smooth page transitions.
 */
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import Sidebar from './Sidebar';
import { pageVariants, pageTransition } from './lib/motion';

const MainLayout = () => {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg)]">
      <Sidebar />

      {/* Content area — offset by sidebar width */}
      <main
        className="flex-1 ml-14 md:ml-[240px] overflow-y-auto relative"
        id="main-content"
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={location.pathname}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="min-h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
};

export default MainLayout;
