import apiClient from "./apiClient";

export async function getArchive(page = 1, pageSize = 20) {
  const response = await apiClient.get("/archive", {
    params: { page, page_size: pageSize },
  });
  return response.data; // { items, total, page, page_size }
}

export async function getArchiveItem(resourceId) {
  const response = await apiClient.get(`/archive/${resourceId}`);
  return response.data; // includes source_url, filename, error_message, status
}

export async function deleteArchiveItem(resourceId) {
  try {
    const response = await apiClient.delete(`/archive/${resourceId}`);
    return response.data;
  } catch (err) {
    if (err.response?.status === 404) {
      return { deleted: true, resource_id: resourceId };
    }
    throw err;
  }
}