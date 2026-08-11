import { Sidebar } from "@/app/layout/sidebar";
import { Navbar } from "@/app/layout/navbar";
import { MobileTabBar } from "@/app/layout/mobile-tab-bar";
import { AuthGuard } from "@/app/components/auth/auth-guard";
import { NativeBackHandler } from "@/app/layout/native-back-handler";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <NativeBackHandler />
      <div className="flex min-h-screen">
        <div className="hidden md:block">
          <Sidebar />
        </div>
        <div className="flex flex-1 flex-col md:pl-64">
          <Navbar />
          <main className="flex-1 p-4 pb-24 md:p-6 md:pb-6">{children}</main>
        </div>
      </div>
      <MobileTabBar />
    </AuthGuard>
  );
}
