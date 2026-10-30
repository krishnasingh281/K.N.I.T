import { Server } from "socket.io";
import { recalculatePipeline } from "../services/allocationService.js";

let io;

// FIX 1: Initialize assignments here so new dashboards don't crash or get undefined
export const clusterState = {
  nodes: {},
  assignments: {},
};

export const initSocketServer = (httpServer) => {
  io = new Server(httpServer, {
    cors: {
      origin: "http://localhost:5173",
      credentials: true,
    },
  });

  console.log("Socket server initialized");

  io.on("connection", (socket) => {
    console.log("A worker or client connected: " + socket.id);

    // Instantly send current state to the newly connected React Dashboard
    socket.emit("cluster_update", clusterState.nodes);
    socket.emit("pipeline_rebuilt", clusterState.assignments || {});

    // 1. Worker joins
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

      // FIX 2: Update the global state with the new math, then broadcast it
      clusterState.assignments = recalculatePipeline(clusterState, io);
      io.emit("pipeline_rebuilt", clusterState.assignments);
    });

    // 2. Heartbeat
    socket.on("heartbeat", () => {
      if (clusterState.nodes[socket.id]) {
        clusterState.nodes[socket.id].lastSeen = Date.now();
      }
    });

    // 3. Clean disconnect
    socket.on("disconnect", () => {
      console.log("❌ A worker disconnected: " + socket.id);
      if (clusterState.nodes[socket.id]) {
        clusterState.nodes[socket.id].status = "dead";
      }

      io.emit("cluster_update", clusterState.nodes);

      // FIX 2 (continued)
      clusterState.assignments = recalculatePipeline(clusterState, io);
      io.emit("pipeline_rebuilt", clusterState.assignments);
    });
  });

  // 4. Fault-Tolerance Loop
  setInterval(() => {
    const now = Date.now();
    let stateChanged = false;

    for (const nodeId in clusterState.nodes) {
      const node = clusterState.nodes[nodeId];
      if (node.status === "active" && now - node.lastSeen > 1500) {
        node.status = "dead";
        console.log(`\n[CRITICAL FAULT] Node ${nodeId} dropped offline!`);
        stateChanged = true;
      }
    }

    if (stateChanged) {
      io.emit("cluster_update", clusterState.nodes);

      // FIX 2 (continued)
      clusterState.assignments = recalculatePipeline(clusterState, io);
      io.emit("pipeline_rebuilt", clusterState.assignments);
    }
  }, 500);
};

export const getIO = () => {
  if (!io) throw new Error("Socket.io not initialized!");
  return io;
};
