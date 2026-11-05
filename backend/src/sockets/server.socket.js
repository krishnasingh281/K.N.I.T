import { Server } from "socket.io";
import { clusterState } from "./clusterState.js";
import { registerClusterEvents, startFaultToleranceLoop } from "./cluster.socket.js";
import { registerChatEvents } from "./chat.socket.js";

let io;

export const initSocketServer = (httpServer) => {
  io = new Server(httpServer, {
    cors: {
      origin: "http://localhost:5173",
      credentials: true,
    },
  });

  console.log("Socket server initialized");

  // Start the background health check
  startFaultToleranceLoop(io, clusterState);

  io.on("connection", (socket) => {
    console.log("A worker or client connected: " + socket.id);

    // Initial state sync for new UI clients
    socket.emit("cluster_update", clusterState.nodes);
    socket.emit("pipeline_rebuilt", clusterState.assignments || {});

    // Register modular controllers, passing the shared state
    registerClusterEvents(io, socket, clusterState);
    registerChatEvents(io, socket, clusterState);
  });
};

export const getIO = () => {
  if (!io) throw new Error("Socket.io not initialized!");
  return io;
};