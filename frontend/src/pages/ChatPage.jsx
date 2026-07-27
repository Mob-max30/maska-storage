import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useChat } from "../hooks/useChat";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const { messages, loading, error, askQuestion } = useChat();

  function handleSubmit(e) {
    e.preventDefault();
    if (input.trim() && !loading) {
      askQuestion(input.trim());
      setInput("");
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-8">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center pt-32">
              <p className="text-2xl text-gray-300">
                What do you want to know?
              </p>
            </div>
          )}

          {messages.map((msg, i) =>
            msg.role === "user" ? (
              <div key={i} className="flex justify-end mb-6">
                <div className="max-w-[75%] rounded-3xl bg-[#303030] px-5 py-2.5 text-white">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div key={i} className="mb-8 text-gray-100 leading-7">
                <div className="prose-invert">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>

                {msg.citations?.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {msg.citations.map((c, ci) => (
                      <span
                        key={ci}
                        className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-gray-400"
                      >
                        {c.title || c.resource_id}
                      </span>
                    ))}
                  </div>
                )}

                {msg.citations?.length === 0 && (
                  <p className="mt-4 text-xs text-gray-500">No sources found</p>
                )}
              </div>
            )
          )}

          {loading && (
            <div className="mb-8 text-gray-500 text-sm">Thinking…</div>
          )}
        </div>
      </div>

      <div className="shrink-0 px-4 pb-6">
        <div className="mx-auto max-w-3xl">
          {error && (
            <p className="mb-2 text-sm text-red-400">{error}</p>
          )}
          <form
            onSubmit={handleSubmit}
            className="flex items-end gap-2 rounded-3xl border border-white/10 bg-[#303030] px-4 py-3"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything"
              disabled={loading}
              className="flex-1 bg-transparent text-white placeholder-gray-500 outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-full bg-white px-4 py-1.5 text-sm font-medium text-black transition-opacity disabled:opacity-30"
            >
              Send
            </button>
          </form>
          <p className="mt-2 text-center text-xs text-gray-500">
            Answers are grounded in your saved resources.
          </p>
        </div>
      </div>
    </div>
  );
}