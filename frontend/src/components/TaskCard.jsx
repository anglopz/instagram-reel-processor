import StatusBadge from "./StatusBadge";
import api from "../services/api";

function timeAgo(dateStr) {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function TaskCard({ task, onSelect, onRefresh }) {
  const canCancel = ["pending", "processing"].includes(task.status);

  const handleCancel = async (e) => {
    e.stopPropagation();
    try {
      await api.post(`/tasks/${task.id}/cancel`);
      onRefresh();
    } catch {
      // ignore — task may already be terminal
    }
  };

  return (
    <div
      onClick={() => onSelect(task)}
      className="bg-surface border border-zinc-800 rounded-lg p-5 hover:border-zinc-700 transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-2">
            <StatusBadge status={task.status} />
          </div>
          <p className="text-sm font-mono text-zinc-400 truncate">
            {task.reel_url}
          </p>
          <div className="flex items-center gap-4 mt-2">
            <span className="text-xs text-zinc-600">
              {timeAgo(task.created_at)}
            </span>
            {task.language && (
              <span className="text-xs text-zinc-500">
                Language: {task.language}
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0">
          {canCancel && (
            <button
              onClick={handleCancel}
              className="text-sm text-zinc-500 hover:text-red-400 transition-all duration-150 cursor-pointer"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
      {task.status === "failed" && task.error_message && (
        <p className="mt-3 text-xs font-mono text-red-400 bg-red-500/5 border border-red-500/10 rounded-md p-3 truncate">
          {task.error_message}
        </p>
      )}
    </div>
  );
}
