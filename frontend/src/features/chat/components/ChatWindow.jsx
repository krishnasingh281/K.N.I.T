import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';

export const ChatWindow = ({ socket }) => {
  const { messages, isGenerating, error, sendMessage } = useChat(socket);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  // Auto-scroll to the bottom whenever messages change (crucial for streaming tokens)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isGenerating) return;
    
    sendMessage(inputValue);
    setInputValue(''); // Clear input after sending
  };

  return (
    <div className="flex flex-col h-[600px] w-full max-w-3xl mx-auto bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-2xl">
      
      {/* Header */}
      <div className="px-6 py-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
          Cluster Inference Chat
        </h2>
        {isGenerating && (
          <span className="text-xs font-medium px-2.5 py-1 bg-blue-500/20 text-blue-400 rounded-full">
            Computing...
          </span>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-900/50 scrollbar-thin scrollbar-thumb-slate-700">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-sm">
            Cluster is standing by. Enter a prompt to begin the relay.
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div 
              key={idx} 
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div 
                className={`max-w-[80%] rounded-2xl px-5 py-3 text-sm leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-br-sm shadow-md' 
                    : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-sm'
                }`}
              >
                {msg.content}
                {/* Blinking cursor effect for the currently generating AI message */}
                {isGenerating && msg.role === 'ai' && idx === messages.length - 1 && (
                  <span className="ml-1 inline-block w-1.5 h-3.5 bg-slate-400 animate-pulse align-middle"></span>
                )}
              </div>
            </div>
          ))
        )}
        
        {/* Error Banner */}
        {error && (
          <div className="p-3 mb-4 text-sm text-red-400 bg-red-900/20 border border-red-900/50 rounded-lg text-center">
            {error}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-slate-800 border-t border-slate-700">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isGenerating || !socket}
            placeholder={isGenerating ? "Cluster is processing..." : "Type your prompt..."}
            className="w-full bg-slate-900 border border-slate-700 text-slate-200 placeholder-slate-500 text-sm rounded-lg pl-4 pr-24 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isGenerating || !socket}
            className="absolute right-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};