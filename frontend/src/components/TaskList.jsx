import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import TaskCard from "./TaskCard";
import TaskDetailModal from "./TaskDetailModal";
import AddTaskModal from "./AddTaskModal";

export default function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [selected, setSelected] = useState(null);

  const fetchTasks = useCallback(async () => {
    try {
      const { data } = await api.get("/tasks");
      setTasks(data.tasks);
    } catch {
      // 401 handled by interceptor
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Poll while active tasks exist
  useEffect(() => {
    const hasActive = tasks.some((t) =>
      ["pending", "processing"].includes(t.status)
    );
    if (!hasActive) return;

    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, [tasks, fetchTasks]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-zinc-800/50 animate-pulse rounded-lg h-24" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-zinc-50">Your Tasks</h2>
        <button
          onClick={() => setShowAdd(true)}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-500 transition-all duration-150 cursor-pointer"
        >
          + New Task
        </button>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-zinc-600">No tasks yet. Add an Instagram Reel URL to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onSelect={setSelected}
              onRefresh={fetchTasks}
            />
          ))}
        </div>
      )}

      {showAdd && (
        <AddTaskModal
          onClose={() => setShowAdd(false)}
          onCreated={fetchTasks}
        />
      )}

      {selected && (
        <TaskDetailModal
          task={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
