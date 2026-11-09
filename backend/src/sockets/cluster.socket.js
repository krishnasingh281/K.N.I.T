import { recalculatePipeline } from "../services/allocationService.js";

export const registerClusterEvents = (io, socket, clusterState) => {
  
  // Worker joins
  socket.on("register", (hardware) => {
    clusterState.nodes[socket.id] = {
      id: socket.id,
      status: "active",
      gpu: hardware.gpu,
      vram: hardware.vram,
      lastSeen: Date.now(),
      joinedAt: Date.now(),
    };
    console.log(`✅ Node Registered: ${hardware.gpu} (${socket.id})`);

    io.emit("cluster_update", clusterState.nodes);
    clusterState.assignments = recalculatePipeline(clusterState, io);
    io.emit("pipeline_rebuilt", clusterState.assignments);
  });

  // Worker heartbeat
  socket.on("heartbeat", () => {
    if (clusterState.nodes[socket.id]) {
      clusterState.nodes[socket.id].lastSeen = Date.now();
    }
  });

  // Worker disconnects gracefully
  socket.on("disconnect", () => {
    console.log("❌ A worker disconnected: " + socket.id);
    if (clusterState.nodes[socket.id]) {
      clusterState.nodes[socket.id].status = "dead";

      // NEW: If the worker is manually closed during an active generation
      if (clusterState.isGenerating) {
        console.log("⚠️ Aborting active inference due to manual node disconnect.");
        clusterState.isGenerating = false;
        io.emit("prompt_error", { 
          message: "A worker node disconnected mid-generation. The pipeline has been automatically re-stitched. Please try your prompt again." 
        });
      }
    }

    io.emit("cluster_update", clusterState.nodes);
    clusterState.assignments = recalculatePipeline(clusterState, io);
    io.emit("pipeline_rebuilt", clusterState.assignments);
  });
};

// The background fault-tolerance loop
export const startFaultToleranceLoop = (io, clusterState) => {
  setInterval(() => {
    const now = Date.now();
    let stateChanged = false;
    let nodeDroppedMidInference = false; // NEW: Track if the drop ruins a current run

    for (const nodeId in clusterState.nodes) {
      const node = clusterState.nodes[nodeId];
      if (node.status === "active" && now - node.lastSeen > 1500) {
        node.status = "dead";
        console.log(`\n[CRITICAL FAULT] Node ${nodeId} dropped offline!`);
        stateChanged = true;

        // NEW: If the heartbeat flatlines while we are actively generating text
        if (clusterState.isGenerating) {
          nodeDroppedMidInference = true;
        }
      }
    }

    if (stateChanged) {
      io.emit("cluster_update", clusterState.nodes);
      clusterState.assignments = recalculatePipeline(clusterState, io);
      io.emit("pipeline_rebuilt", clusterState.assignments);

      // NEW: Abort and unlock the UI
      if (nodeDroppedMidInference) {
        console.log("⚠️ Aborting active inference due to pipeline collapse.");
        clusterState.isGenerating = false;
        
        io.emit("prompt_error", { 
          message: "A worker node crashed mid-generation. The pipeline has been automatically re-stitched. Please try your prompt again." 
        });
      }
    }
  }, 500);
};