import { useArchive } from "../hooks/useArchive";

const STATUS_STYLES = {
  ready: "text-green-700 bg-green-50",
  processing: "text-yellow-700 bg-yellow-50",
  pending: "text-gray-700 bg-gray-50",
  failed: "text-red-700 bg-red-50",
};

export default function ArchivePage() {
  const { items, total, loading, error, removeItem } = useArchive();

  if (loading) return <p className="p-6 text-gray-500">Loading archive...</p>;
  if (error) return <p className="p-6 text-red-600">{error}</p>;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-1">Archive</h1>
      <p className="text-sm text-gray-500 mb-4">{total} resource(s)</p>

      {items.length === 0 && <p className="text-gray-500">No items yet.</p>}

      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex justify-between items-center border rounded px-3 py-2"
          >
            <div>
              <span className="font-medium">{item.title || "Untitled"}</span>
              <span
                className={`ml-2 text-xs px-2 py-0.5 rounded ${STATUS_STYLES[item.status] || ""}`}
              >
                {item.status}
              </span>
            </div>
            <button
              onClick={() => removeItem(item.id)}
              className="text-red-600 text-sm"
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}