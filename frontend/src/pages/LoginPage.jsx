import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-dark px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-zinc-50 text-center mb-8">
          Reel Processor
        </h1>
        <form
          onSubmit={handleSubmit}
          className="bg-surface border border-zinc-800 p-8 rounded-lg"
        >
          <h2 className="text-lg font-semibold text-zinc-50 mb-4">Log in</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-surface-dark border border-zinc-800 text-zinc-50 rounded-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-surface-dark border border-zinc-800 text-zinc-50 rounded-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
              />
            </div>
          </div>
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="mt-4 w-full py-3 px-4 font-medium text-white bg-blue-600 rounded-md hover:bg-blue-500 disabled:opacity-50 transition-all duration-150 cursor-pointer"
          >
            {loading ? "Logging in..." : "Log in"}
          </button>
          <p className="mt-4 text-sm text-center text-zinc-500">
            Don't have an account?{" "}
            <Link to="/register" className="text-blue-500 hover:text-blue-400">
              Register
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
