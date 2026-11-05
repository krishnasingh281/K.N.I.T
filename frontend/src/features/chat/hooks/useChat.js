import { useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { addMessage } from '../chatSlice';
import { 
  registerChatListeners, 
  removeChatListeners, 
  submitPromptService 
} from '../services/chatSocket.service';

/**
 * Orchestrates the chat state and socket services.
 * @param {Object} socket - The Socket.io client instance
 */
export const useChat = (socket) => {
  const dispatch = useDispatch();
  
  // Extract state from our chatSlice
  const { messages, isGenerating, error } = useSelector((state) => state.chat);

  // Bind socket events to Redux when the component mounts
  useEffect(() => {
    if (!socket) return;

    registerChatListeners(socket, dispatch);

    // Cleanup listeners on unmount to prevent memory leaks or duplicate events
    return () => {
      removeChatListeners(socket);
    };
  }, [socket, dispatch]);

  // Expose a clean function for the UI to send a message
  const sendMessage = useCallback((prompt) => {
    if (!prompt.trim() || !socket || isGenerating) return;

    // 1. Immediately update local state so the user sees their message
    dispatch(addMessage({ role: 'user', content: prompt }));

    // 2. Fire the network request to the Master Node
    submitPromptService(socket, prompt);
    
  }, [socket, dispatch, isGenerating]);

  // Return exactly what the UI component needs—nothing more
  return {
    messages,
    isGenerating,
    error,
    sendMessage
  };
};