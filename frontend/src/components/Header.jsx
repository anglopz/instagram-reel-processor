import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-40 h-16 bg-surface-dark/80 backdrop-blur-sm border-b border-zinc-800 px-6 flex items-center justify-between">
      <h1 className="text-xl font-semibold text-zinc-50">
        Reel Processor
      </h1>
      <div className="flex items-center gap-4">
        <span className="text-sm font-mono text-zinc-500">{user?.email}</span>
        <button
          onClick={handleLogout}
          className="text-sm text-zinc-500 hover:text-zinc-300 transition-all duration-150 cursor-pointer"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
