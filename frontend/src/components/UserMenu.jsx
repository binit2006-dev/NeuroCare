import { LogIn, LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function UserMenu() {
  const { user, loading, login, logout } = useAuth();
  if (loading) return <div className="w-24 h-9" />;

  if (!user) {
    return (
      <button
        data-testid="google-signin-button"
        onClick={login}
        className="ml-1 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary text-primary-foreground text-sm hover:bg-[#3a6347] hover:-translate-y-[1px]"
      >
        <LogIn className="w-4 h-4" /> Sign in
      </button>
    );
  }

  return (
    <div className="ml-1 flex items-center gap-2">
      {user.picture ? (
        <img data-testid="user-avatar" src={user.picture} alt={user.name} className="w-8 h-8 rounded-full border border-border" />
      ) : (
        <span data-testid="user-avatar" className="w-8 h-8 rounded-full bg-primary/15 text-primary text-sm flex items-center justify-center">
          {user.name?.[0]}
        </span>
      )}
      <button
        data-testid="logout-button"
        onClick={logout}
        aria-label="Sign out"
        className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-primary/10 text-foreground/70"
      >
        <LogOut className="w-4 h-4" />
      </button>
    </div>
  );
}
