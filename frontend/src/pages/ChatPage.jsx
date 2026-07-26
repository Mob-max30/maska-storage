import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useChat } from "../hooks/useChat";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const { messages, loading, error, askQuestion } = useChat();

  function handleSubmit(e) {
    e.preventDefault();
    if (input.trim()) {
      askQuestion(input.trim());
      setInput("");
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 flex flex-col h-full">
      <h1 className="text-2xl font-semibold mb-4">Chat</h1>

      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "user" ? "text-right" : "text-left"}>
            <div className="inline-block bg-gray-100 rounded px-3 py-2 max-w-[85%]">
              <ReactMarkdown>{msg.content}</ReactMarkdown>

              {msg.role === "assistant" && msg.citations?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-500">
                  <p className="font-medium mb-1">Sources:</p>
                  {msg.citations.map((c, ci) => (
                    <div key={ci} className="mb-1">
                      {c.title || c.resource_id}
                    </div>
                  ))}
                </div>
              )}

              {msg.role === "assistant" && msg.citations?.length === 0 && (
                <p className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-400">
                  No sources found
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {error && <p className="text-red-600 mb-2">{error}</p>}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 border rounded px-3 py-2"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? "Thinking..." : "Send"}
        </button>
      </form>
    </div>
  );
}