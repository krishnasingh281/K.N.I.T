import { useSelector } from "react-redux";
import { selectAllNodes } from "../dashboardSlice.js";
import { useCluster } from "../hooks/useCluster.js";
import { ServerCard } from "../components/ServerCard";

export const Dashboard = () => {
  // 1. Activate the Orchestrator (Starts the socket listener)
  useCluster();

  // 2. Grab the perfectly formatted Array of nodes from Redux
  const nodes = useSelector(selectAllNodes);
  const assignments = useSelector((state) => state.cluster.assignments);

  // Calculate some quick stats for the header
  const activeNodes = nodes.filter((n) => n.status === "active").length;

  return (
    <div className="min-h-screen bg-slate-950 p-8 md:p-12 font-sans selection:bg-cyan-500/30">
      <div className="max-w-7xl mx-auto">
        {/* Dashboard Header */}
        <header className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">
              Cluster Observability
            </h1>
            <p className="text-slate-400 text-sm">
              Real-time topology and hardware metrics for the Knit inference
              engine.
            </p>
          </div>

          {/* Quick Stats Pill */}
          <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 px-5 py-3 rounded-lg shadow-sm">
            <div className="flex flex-col">
              <span className="text-xs text-slate-500 font-medium">
                ACTIVE WORKERS
              </span>
              <span className="text-xl font-bold text-cyan-400">
                {activeNodes}
              </span>
            </div>
            <div className="h-8 w-px bg-slate-800"></div>
            <div className="flex flex-col">
              <span className="text-xs text-slate-500 font-medium">
                TOTAL NODES
              </span>
              <span className="text-xl font-bold text-white">
                {nodes.length}
              </span>
            </div>
          </div>
        </header>

        {/* Server Grid */}
        {nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 border-2 border-dashed border-slate-800 rounded-2xl bg-slate-900/50">
            <div className="animate-pulse bg-slate-800 h-12 w-12 rounded-full mb-4 flex items-center justify-center">
              <span className="text-cyan-500 text-2xl">📡</span>
            </div>
            <h3 className="text-slate-300 font-medium text-lg mb-1">
              Waiting for Workers
            </h3>
            <p className="text-slate-500 text-sm">
              No Python nodes have connected to the Master Node yet.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {nodes.map((node) => (
              <ServerCard
                key={node.id}
                node={node}
                assignment={assignments[node.id]} // <-- NEW: Pass the math down
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
