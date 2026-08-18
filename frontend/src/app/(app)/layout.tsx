import { AuthGuard } from "@/app/components/auth/auth-guard";
import { AppShell } from "@/app/layout/AppShell";
import { NotificationNavigator } from "@/app/hooks/notification-navigation";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <NotificationNavigator>
        <AppShell>{children}</AppShell>
      </NotificationNavigator>
    </AuthGuard>
  );
}
