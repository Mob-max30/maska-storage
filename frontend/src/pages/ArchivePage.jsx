import { useArchive } from "../hooks/useArchive";

const STATUS_STYLES = {
  ready: "bg-green-500/10 text-green-400 border-green-500/20",
  processing: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  pending: "bg-white/5 text-gray-400 border-white/10",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
};

export default function ArchivePage() {
  const { items, total, loading, error, removeItem } = useArchive();

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-2xl font-medium text-white mb-2">Archive</h1>
        <p className="text-sm text-gray-400 mb-8">
          {loading ? "Loading…" : `${total} resource${total === 1 ? "" : "s"}`}
        </p>

        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="rounded-2xl border border-dashed border-white/15 px-6 py-12 text-center">
            <p className="text-sm text-gray-300">Nothing saved yet</p>
            <p className="mt-1 text-xs text-gray-500">
              Upload a URL or PDF to get started.
            </p>
          </div>
        )}

        <div className="divide-y divide-white/5">
          {items.map((item) => (
            <div
              key={item.id}
              className="group flex items-center justify-between gap-4 py-4"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm text-white">
                    {item.title || "Untitled"}
                  </span>
                  <span
                    className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${STATUS_STYLES[item.status] || STATUS_STYLES.pending
                      }`}
                  >
                    {item.status}
                  </span>
                </div>
                {item.summary && (
                  <p className="mt-1 truncate text-xs text-gray-500">
                    {item.summary}
                  </p>
                )}
              </div>
              <button
                onClick={() => removeItem(item.id)}
                className="shrink-0 rounded-lg px-3 py-1.5 text-xs text-gray-500 opacity-0 transition-opacity hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}