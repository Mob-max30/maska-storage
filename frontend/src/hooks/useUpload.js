import { useEffect, useRef, useState } from "react";
import { uploadUrl, uploadPdf } from "../services/uploadService";
import { getArchiveItem } from "../services/archiveService";

// 60 attempts x 3s = 3 minutes of polling before we give up.
// Long documents (e.g. full Wikipedia articles, large PDFs) can take
// well over a minute end-to-end, so this needs real headroom.
const MAX_POLL_ATTEMPTS = 60;
const POLL_INTERVAL_MS = 3000;

export function useUpload() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Guards against: (1) setting state after the component has unmounted,
  // and (2) a second upload starting while an earlier poll loop is still
  // running — each poll cycle is tagged with an id, and a cycle only
  // applies its result if it's still the current one.
  const isMountedRef = useRef(true);
  const pollIdRef = useRef(0);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  function pollUntilDone(resourceId) {
    pollIdRef.current += 1;
    const currentPollId = pollIdRef.current;
    let attempts = 0;

    const poll = async () => {
      // A newer upload started, or the component unmounted — stop silently.
      if (!isMountedRef.current || pollIdRef.current !== currentPollId) {
        return;
      }

      attempts += 1;

      try {
        const item = await getArchiveItem(resourceId);

        console.log("Polling Resource ID:", resourceId);
        console.log("Polling Response:", item);

        if (!isMountedRef.current || pollIdRef.current !== currentPollId) {
          return;
        }

        if (item.status === "ready" || item.status === "failed") {
          setResult(item);
          setLoading(false);
          return;
        }

        if (attempts >= MAX_POLL_ATTEMPTS) {
          setError(
            "This is taking longer than expected. Check the Archive page in a bit — your upload may still be processing."
          );
          setLoading(false);
          return;
        }

        setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (!isMountedRef.current || pollIdRef.current !== currentPollId) {
          return;
        }
        setError(
          err.response?.data?.error?.message || "Failed to check upload status"
        );
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