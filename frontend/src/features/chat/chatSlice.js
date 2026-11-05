import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  messages: [], // Array of { role: 'user' | 'ai', content: string }
  isGenerating: false,
  error: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    // Adds a full message (used for the user's initial prompt)
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    // The "Typewriter": Finds the last AI message and appends the new token
    appendTokenToLastMessage: (state, action) => {
      const lastMessage = state.messages[state.messages.length - 1];
      if (lastMessage && lastMessage.role === 'ai') {
        lastMessage.content += action.payload.token;
      }
    },
    setGenerating: (state, action) => {
      state.isGenerating = action.payload;
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
    clearChat: (state) => {
      state.messages = [];
      state.error = null;
    }
  },
});

export const { 
  addMessage, 
  appendTokenToLastMessage, 
  setGenerating, 
  setError, 
  clearChat 
} = chatSlice.actions;

export default chatSlice.reducer;