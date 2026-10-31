import { socket } from "../../../app/socket.js"; 

/**
 * Subscribes to real-time cluster updates from the Master Node.
 * @param {Function} onUpdateCallback - The function to run when data arrives
 */
export const subscribeToClusterUpdates = (onUpdateCallback) => {
  socket.on("cluster_update", (data) => {
    // We receive the nested object from the backend and pass it to the callback
    onUpdateCallback(data);
  });
};

/**
 * Removes the listener to prevent memory leaks when the dashboard unmounts.
 */
export const unsubscribeFromClusterUpdates = () => {
  socket.off("cluster_update");
};

export const subscribeToPipelineUpdates = (onUpdateCallback) => {
  socket.on("pipeline_rebuilt", (data) => {
    onUpdateCallback(data);
  });
};

export const unsubscribeFromPipelineUpdates = () => {
  socket.off("pipeline_rebuilt");
};