import { useState } from "react";
import api from "../services/api";

export default function AddTaskModal({ onClose, onCreated }) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!url.startsWith("http")) {
      setError("URL must start with http:// or https://");
      return;
    }

    setLoading(true);
    try {
      await api.post("/tasks", { reel_url: url });
      onCreated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create task");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-surface border border-zinc-800 rounded-lg shadow-2xl shadow-black/50 w-full max-w-md mx-4 p-6">
        <h2 className="text-lg font-semibold text-zinc-50 mb-4">
          Process a Reel
        </h2>
        <form onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-zinc-400 mb-1.5">
            Instagram Reel URL
          </label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.instagram.com/reel/..."
            className="w-full px-4 py-3 bg-surface-dark border border-zinc-800 text-zinc-50 font-mono text-sm rounded-md placeholder-zinc-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
            autoFocus
          />
          {error && (
            <p className="mt-2 text-sm text-red-400">{error}</p>
          )}
          <div className="mt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-500 hover:text-zinc-300 transition-all duration-150 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-500 disabled:opacity-50 transition-all duration-150 cursor-pointer"
            >
              {loading ? "Submitting..." : "Submit"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
