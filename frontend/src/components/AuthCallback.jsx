import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { exchangeSession } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const match = location.hash.match(/session_id=([^&]+)/);
    if (!match) { navigate("/", { replace: true }); return; }
    exchangeSession(match[1])
      .then((user) => {
        setUser(user);
        toast.success(`Welcome, ${user.name.split(" ")[0]}`);
        navigate("/history", { replace: true, state: { user } });
      })
      .catch(() => {
        toast.error("Sign-in failed. Please try again.");
        navigate("/", { replace: true });
      });
  }, [location.hash, navigate, setUser]);

  return <div data-testid="auth-callback" className="min-h-screen" />;
}
