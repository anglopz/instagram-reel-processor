import { useEffect, useState } from "react";
import StatusBadge from "./StatusBadge";
import api from "../services/api";

export default function TaskDetailModal({ task, onClose }) {
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (task.status !== "completed") return;
    setLoading(true);
    api
      .get(`/tasks/${task.id}/transcript`)
      .then(({ data }) => setTranscript(data))
      .catch(() => setTranscript(null))
      .finally(() => setLoading(false));
  }, [task.id, task.status]);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-surface border border-zinc-800 rounded-lg shadow-2xl shadow-black/50 w-full max-w-lg mx-4 p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-semibold text-zinc-50">Task Detail</h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-xl leading-none transition-all duration-150 cursor-pointer"
          >
            &times;
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
              URL
            </label>
            <p className="text-sm font-mono text-zinc-300 break-all mt-1">{task.reel_url}</p>
          </div>

          <div>
            <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
              Status
            </label>
            <div className="mt-1">
              <StatusBadge status={task.status} />
            </div>
          </div>

          {task.status === "failed" && task.error_message && (
            <div>
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                Error
              </label>
              <p className="text-sm font-mono text-red-400 mt-1 bg-red-500/5 border border-red-500/10 rounded-md p-3">
                {task.error_message}
              </p>
            </div>
          )}

          {task.status === "completed" && (
            <>
              {loading ? (
                <p className="text-sm text-zinc-500">Loading transcript...</p>
              ) : transcript ? (
                <>
                  <div>
                    <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                      Language
                    </label>
                    <div className="mt-1">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium font-mono bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        {transcript.language || "unknown"}
                      </span>
                    </div>
                  </div>

                  {transcript.topics && transcript.topics.length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                        Topics
                      </label>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {transcript.topics.map((topic) => (
                          <span
                            key={topic}
                            className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono bg-zinc-800 text-zinc-300"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                      Transcript
                    </label>
                    <div className="mt-1 p-4 bg-surface-dark rounded-md font-mono text-sm text-zinc-300 whitespace-pre-wrap max-h-64 overflow-y-auto border border-zinc-800">
                      {transcript.transcript}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-zinc-500">
                  Transcript unavailable.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
