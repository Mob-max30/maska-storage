import { useState, useEffect, useCallback } from "react";
import { getArchive, deleteArchiveItem } from "../services/archiveService";

export function useArchive(page = 1, pageSize = 20) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getArchive(page, pageSize);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Failed to load archive");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  async function removeItem(resourceId) {
    await deleteArchiveItem(resourceId);
    setItems((prev) => prev.filter((item) => item.id !== resourceId));
    setTotal((prev) => Math.max(0, prev - 1));
  }

  return { items, total, loading, error, refetch: fetchItems, removeItem };
}