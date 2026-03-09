import Header from "../components/Header";
import TaskList from "../components/TaskList";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-3xl mx-auto px-4 py-8">
        <TaskList />
      </main>
    </div>
  );
}
