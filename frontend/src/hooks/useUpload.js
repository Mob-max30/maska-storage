import { useState } from "react";
import { uploadUrl, uploadPdf } from "../services/uploadService";
import { getArchiveItem } from "../services/archiveService";

const MAX_POLL_ATTEMPTS = 20;
const POLL_INTERVAL_MS = 3000;

export function useUpload() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  function pollUntilDone(resourceId) {
    let attempts = 0;

    const poll = async () => {
      attempts += 1;
      try {
        const item = await getArchiveItem(resourceId);

        if (item.status === "ready" || item.status === "failed") {
          setResult(item);
          setLoading(false);
          return;
        }

        if (attempts >= MAX_POLL_ATTEMPTS) {
          setError(
            "Still processing — the AI pipeline isn't connected yet. Check the Archive page later."
          );
          setLoading(false);
          return;
        }

        setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        setError(err.response?.data?.error?.message || "Failed to check upload status");
        setLoading(false);
      }
    };

    poll();
  }

  async function submitUrl(url) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await uploadUrl(url);
      pollUntilDone(data.resource_id);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Upload failed");
      setLoading(false);
    }
  }

  async function submitPdf(file) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await uploadPdf(file);
      pollUntilDone(data.resource_id);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Upload failed");
      setLoading(false);
    }
  }

  return { loading, error, result, submitUrl, submitPdf };
}