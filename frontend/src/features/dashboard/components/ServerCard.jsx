export const ServerCard = ({ node, assignment }) => {
  const isActive = node.status === "active";

  return (
    <div className="flex flex-col p-5 bg-slate-800 border border-slate-700 rounded-xl shadow-lg hover:shadow-cyan-900/20 transition-all duration-300">
      {/* Header: Node ID & Status Badge */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-mono font-medium text-slate-300 truncate w-3/4">
          {node.id}
        </h3>
        <div
          className={`flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold tracking-wide ${
            isActive
              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
          }`}
        >
          {isActive && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
          )}
          {isActive ? "LIVE" : "DEAD"}
        </div>
      </div>

      {/* Hardware Specs */}
      <div className="space-y-3 mb-5 flex-grow">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 uppercase tracking-wider">
            GPU
          </span>
          <span className="text-sm font-semibold text-slate-100">
            {node.gpu}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 uppercase tracking-wider">
            VRAM
          </span>
          <span className="text-sm font-semibold text-slate-100">
            {node.vram}
          </span>
        </div>
      </div>

      {/* Workload / Layer Assignment */}
      <div className="mt-2 mb-4 p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
        <div className="text-[10px] text-slate-500 font-bold tracking-wider mb-2 uppercase">
          Pipeline Assignment
        </div>
        {assignment && isActive ? (
          <div className="flex justify-between items-center">
            <div>
              <div className="text-xs text-slate-400">Layers</div>
              <div className="text-sm font-mono text-cyan-400 font-bold">
                {assignment.startLayer} - {assignment.endLayer}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-400">Position</div>
              <div className="text-sm font-medium text-white">
                Node {assignment.orderIndex}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500 italic">
            Waiting for assignment...
          </div>
        )}
      </div>

      {/* Footer: Diagnostic Info */}
      <div className="pt-3 border-t border-slate-700/50 flex justify-between text-[11px] text-slate-500">
        <span>Joined: {new Date(node.joinedAt).toLocaleTimeString()}</span>
        <span>Ping: {new Date(node.lastSeen).getSeconds()}s ago</span>
      </div>
    </div>
  );
};
