import apiClient from "./apiClient";

// Single POST /upload endpoint handles both URL and PDF via multipart/form-data
export async function uploadUrl(url) {
  const formData = new FormData();
  formData.append("url", url);

  const response = await apiClient.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data; // { resource_id, status, source_type, title, summary, created_at }
}

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}