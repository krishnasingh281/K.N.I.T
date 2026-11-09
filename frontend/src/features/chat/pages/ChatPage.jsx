/**
 * ChatPage — route: /chat
 * Thin page wrapper around ChatWindow.
 * Props: socket (Socket.io instance from app/socket.js, passed via route)
 */
import { ChatWindow } from '../components/ChatWindow';

export const ChatPage = ({ socket }) => {
  return <ChatWindow socket={socket} />;
};
