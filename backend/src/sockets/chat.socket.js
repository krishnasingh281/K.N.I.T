export const registerChatEvents = (io, socket, clusterState) => {
  
  // 1. Route prompt from UI to Worker 1
  socket.on("submit_prompt", (payload) => {
    const { prompt } = payload;
    console.log(`\n💬 [Prompt Router] Received prompt from UI: "${prompt}"`);

    const assignments = clusterState.assignments;
    if (Object.keys(assignments).length === 0) {
      socket.emit("prompt_error", { message: "No active nodes to process this request." });
      return;
    }

    let headNodeId = null;
    for (const [nodeId, assignment] of Object.entries(assignments)) {
      if (assignment.orderIndex === 1) {
        headNodeId = nodeId;
        break;
      }
    }

    if (!headNodeId) {
      socket.emit("prompt_error", { message: "Routing failure: Pipeline head missing." });
      return;
    }

    console.log(`🚀 [Prompt Router] Routing prompt to Node ${headNodeId} (Worker 1)`);
    io.to(headNodeId).emit("start_inference", { prompt });
    socket.emit("inference_started"); 
  });

  // 2. Stream tokens from Workers to UI
  socket.on("stream_token", (payload) => {
    io.emit("token_received", payload);
  });

  // 3. Notify UI of completion
  socket.on("inference_complete", () => {
    console.log("✅ [Inference] Generation complete. Notifying UI.");
    io.emit("generation_done");
  });
};