import React from 'react';
import { ChatWindow } from '../components/ChatWindow';

export const ChatPage = ({ socket }) => {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6">
      
      {/* Page-Level Header */}
      <div className="w-full max-w-3xl mb-8">
        <h1 className="text-3xl font-bold text-slate-100 tracking-tight">
          Inference Hub
        </h1>
        <p className="text-slate-400 text-sm mt-2">
          Submit prompts to the distributed cluster. The Master Node will route your request to the active workers.
        </p>
      </div>

      {/* The Chat Component */}
      <ChatWindow socket={socket} />
      
    </div>
  );
};