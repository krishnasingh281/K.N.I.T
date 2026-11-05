import { 
  addMessage, 
  appendTokenToLastMessage, 
  setGenerating, 
  setError 
} from '../chatSlice';

/**
 * Emits the prompt to the Node.js Master Node.
 */
export const submitPromptService = (socket, prompt) => {
  socket.emit('submit_prompt', { prompt });
};

/**
 * Registers all chat-related socket listeners and binds them to Redux dispatches.
 */
export const registerChatListeners = (socket, dispatch) => {
  
  socket.on('inference_started', () => {
    dispatch(setGenerating(true));
    dispatch(setError(null));
    // Inject an empty AI message into the state so the streamer has a target to append to
    dispatch(addMessage({ role: 'ai', content: '' }));
  });

  socket.on('token_received', (payload) => {
    // Payload from backend should be { token: "word" }
    dispatch(appendTokenToLastMessage({ token: payload.token }));
  });

  socket.on('generation_done', () => {
    dispatch(setGenerating(false));
  });

  socket.on('prompt_error', (payload) => {
    dispatch(setError(payload.message));
    dispatch(setGenerating(false));
  });
};

/**
 * Cleans up listeners to prevent memory leaks on component unmount.
 */
export const removeChatListeners = (socket) => {
  socket.off('inference_started');
  socket.off('token_received');
  socket.off('generation_done');
  socket.off('prompt_error');
};