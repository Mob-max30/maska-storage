import { useState } from "react";
import { sendChatMessage } from "../services/chatService";

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function askQuestion(question, resourceIds = null) {
    setError(null);
    setLoading(true);
    setMessages((prev) => [...prev, { role: "user", content: question }]);

    try {
      const data = await sendChatMessage(question, resourceIds);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          citations: data.citations,
          resourceIdsUsed: data.resource_ids_used,
        },
      ]);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return { messages, loading, error, askQuestion };
}