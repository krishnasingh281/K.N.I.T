import { io } from "socket.io-client";

// Make sure the port matches your Express server (e.g., 3000, 5000, or 8080)
const socket = io("http://localhost:3000");

socket.on("connect", () => {
  console.log("Connected to the Orchestrator!");

  // "Registering" is literally just emitting this one event
  socket.emit("register", {
    gpu: "NVIDIA RTX 2010",
    vram: "8GB",
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

  // --------------------------------------------------------
  // SIMULATED INFERENCE PIPELINE
  // --------------------------------------------------------
  socket.on("start_inference", (payload) => {
    console.log(
      `\n🚀 [Worker 1] Received prompt from Master: "${payload.prompt}"`,
    );
    console.log("🧠 Simulating tensor math and token generation...");

    // A fake response to stream back
    const simulatedResponse =
      "Hello! I am your distributed AI cluster. I have successfully processed your prompt through my layers across the network.";
    const words = simulatedResponse.split(" ");
    let currentIndex = 0;

    // Stream words one-by-one every 100ms to simulate GPU generation speed
    const streamInterval = setInterval(() => {
      if (currentIndex < words.length) {
        // Add a space after each word
        const token = words[currentIndex] + " ";

        // Blast the token back to the Master Node
        socket.emit("stream_token", { token });

        // Print it to the terminal so you can see it working locally
        process.stdout.write(token);
        currentIndex++;
      } else {
        // Done generating
        clearInterval(streamInterval);
        socket.emit("inference_complete");
        console.log("\n✅ Generation complete. Awaiting next prompt.");
      }
    }, 100);
  });
});

socket.on("disconnect", () => {
  console.log("\nDisconnected from Orchestrator");
});
