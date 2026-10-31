import { io } from "socket.io-client";

// Export the socket instance directly
export const socket = io("http://localhost:3000", {
  withCredentials: true,
});

socket.on("connect", () => {
  console.log("Connected to the Master Node!");
});
