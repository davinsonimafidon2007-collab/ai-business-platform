import { Sidebar } from "@/app/layout/sidebar";
import { Navbar } from "@/app/layout/navbar";
import { AuthGuard } from "@/app/components/auth/auth-guard";

export default function DealsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex flex-1 flex-col pl-64">
          <Navbar />
          <main className="flex-1 p-6">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
