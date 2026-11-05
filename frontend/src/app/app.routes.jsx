import { createBrowserRouter } from "react-router";
import { Dashboard } from "../features/dashboard/pages/Dashboard";
import { ChatPage } from "../features/chat/pages/ChatPage";
import { socket } from "./socket";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Dashboard />,
  },
  {
    path: "/chat",
    element: <ChatPage socket={socket}/>,
  },
]);
