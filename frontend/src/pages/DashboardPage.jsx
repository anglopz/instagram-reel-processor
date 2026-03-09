import Header from "../components/Header";
import TaskList from "../components/TaskList";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-surface-dark">
      <div className="h-0.5 bg-blue-500" />
      <Header />
      <main className="max-w-5xl mx-auto px-6 py-8">
        <TaskList />
      </main>
    </div>
  );
}
