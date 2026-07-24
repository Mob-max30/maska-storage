import apiClient from "./apiClient";

// No streaming — single request, single JSON response
export async function sendChatMessage(question, resourceIds = null) {
  const response = await apiClient.post("/chat", {
    question,
    resource_ids: resourceIds,
  });
  return response.data; // { answer, citations, resource_ids_used }
}