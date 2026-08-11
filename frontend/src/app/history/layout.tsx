import { AuthGuard } from "@/app/components/auth/auth-guard";
import { AppShell } from "@/app/layout/AppShell";

export default function HistoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}