import { io } from "socket.io-client";

// Make sure the port matches your Express server (e.g., 3000, 5000, or 8080)
const socket = io("http://localhost:3000");

socket.on("connect", () => {
  console.log("Connected to the Orchestrator!");

  // "Registering" is literally just emitting this one event
  socket.emit("register", {
    gpu: "NVIDIA RTX 4090",
    vram: "24GB",
  });

  // Listen for the Master Node telling us our layer assignments
  socket.on("pipeline_rebuilt", (assignments) => {
    // Look up just my specific assignment from the master payload
    if (!assignments || !assignments[socket.id]) {
      return;
    }

    const myAssignment = assignments[socket.id];
    console.log("\n🎯 My new layer assignment:", myAssignment);
  });

  // Start sending a heartbeat pulse every 500 milliseconds
  setInterval(() => {
    socket.emit("heartbeat");
    // This just prints a little heart in your terminal so you can see it working
    process.stdout.write("💓 ");
  }, 500);
});

socket.on("disconnect", () => {
  console.log("\nDisconnected from Orchestrator");
});
