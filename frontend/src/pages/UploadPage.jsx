import { useState } from "react";
import { useUpload } from "../hooks/useUpload";

export default function UploadPage() {
  const [url, setUrl] = useState("");
  const { loading, error, result, submitUrl, submitPdf } = useUpload();

  function handleUrlSubmit(e) {
    e.preventDefault();
    if (url.trim()) submitUrl(url.trim());
  }

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) submitPdf(file);
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-12">
        <h1 className="text-2xl font-medium text-white mb-2">Upload content</h1>
        <p className="text-sm text-gray-400 mb-8">
          Save a URL or PDF to make it searchable.
        </p>

        <form onSubmit={handleUrlSubmit} className="mb-6">
          <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-[#303030] px-4 py-3">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/article"
              disabled={loading}
              className="flex-1 bg-transparent text-white placeholder-gray-500 outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="rounded-full bg-white px-4 py-1.5 text-sm font-medium text-black disabled:opacity-30"
            >
              Save
            </button>
          </div>
        </form>

        <label className="block cursor-pointer rounded-2xl border border-dashed border-white/15 bg-white/[0.02] px-6 py-10 text-center transition-colors hover:border-white/30">
          <input
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            disabled={loading}
            className="hidden"
          />
          <span className="text-sm text-gray-300">Click to upload a PDF</span>
          <span className="mt-1 block text-xs text-gray-500">
            PDF only, max 50 MB
          </span>
        </label>

        {loading && (
          <p className="mt-6 text-sm text-gray-400">Uploading and processing…</p>
        )}

        {error && (
          <div className="mt-6 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {result?.status === "ready" && (
          <div className="mt-6 rounded-xl border border-green-500/20 bg-green-500/10 px-4 py-3">
            <p className="text-sm font-medium text-green-300">
              Ready: {result.title}
            </p>
            {result.summary && (
              <p className="mt-1 text-sm text-gray-400">{result.summary}</p>
            )}
          </div>
        )}

        {result?.status === "failed" && (
          <div className="mt-6 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
            <p className="text-sm font-medium text-red-300">Processing failed</p>
            {result.error_message && (
              <p className="mt-1 text-sm text-gray-400">
                {result.error_message}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}