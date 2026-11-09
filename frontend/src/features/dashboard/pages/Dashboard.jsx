/**
 * Dashboard page — route: /dashboard
 * Cluster observability view.
 * Data flow: socket → dashboard.service.js → useCluster hook → Redux → here
 */
import { motion } from 'framer-motion';
import { useSelector } from 'react-redux';
import { selectAllNodes } from '../dashboardSlice';
import { useCluster } from '../hooks/useCluster';
import { NodeCard } from '../components/NodeCard';
import { StatCard } from '../components/StatCard';
import { listVariants, cardVariants } from '../../../shared/lib/motion';

export const Dashboard = () => {
  // Activate socket listeners → populates Redux store
  useCluster();

  const nodes       = useSelector(selectAllNodes);
  const assignments = useSelector((state) => state.cluster.assignments);

  const activeNodes = nodes.filter((n) => n.status === 'active' || n.status === 'healthy').length;
  const deadNodes   = nodes.filter((n) => n.status === 'dead').length;

  // Aggregate VRAM from nodes that carry numeric fields
  const totalVram = nodes.reduce((acc, n) => acc + (n.vramTotal ?? 0), 0);

  // Layers assigned from pipeline data
  const layersAssigned = Object.values(assignments).reduce(
    (acc, a) => acc + (a.endLayer - a.startLayer + 1),
    0
  );

  return (
    <div className="px-8 md:px-10 py-10 max-w-[1200px] mx-auto w-full">

      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-lg font-medium text-[var(--text)]">Dashboard</h1>
        <p className="text-sm text-[var(--text-muted)] mt-0.5">Cluster overview</p>
      </div>

      {/* Summary stats */}
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10"
        variants={listVariants}
        initial="initial"
        animate="animate"
      >
        <motion.div variants={cardVariants}>
          <StatCard
            label="Active Nodes"
            value={activeNodes}
            valueColor="var(--accent)"
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <StatCard
            label="Dead Nodes"
            value={deadNodes}
            valueColor={deadNodes > 0 ? 'var(--danger)' : 'var(--text)'}
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <StatCard
            label="Total VRAM"
            value={totalVram > 0 ? `${totalVram} GB` : '—'}
          />
        </motion.div>
        <motion.div variants={cardVariants}>
          <StatCard
            label="Layers Assigned"
            value={layersAssigned > 0 ? layersAssigned : '—'}
          />
        </motion.div>
      </motion.div>

      {/* Node grid */}
      <div className="mb-4">
        <h2 className="text-sm font-medium text-[var(--text)]">Nodes</h2>
      </div>

      {nodes.length === 0 ? (
        <p className="text-sm text-[var(--text-faint)]">
          No nodes connected to the master.
        </p>
      ) : (
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4"
          variants={listVariants}
          initial="initial"
          animate="animate"
        >
          {nodes.map((node) => (
            <NodeCard
              key={node.id}
              node={node}
              assignment={assignments[node.id]}
            />
          ))}
        </motion.div>
      )}
    </div>
  );
};
