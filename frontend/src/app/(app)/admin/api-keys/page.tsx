"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/app/store/auth-store";
import {
  listAdminApiKeys,
  revokeAdminApiKey,
} from "@/app/services/adminApiKeys";

export default function AdminApiKeysPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, isLoading: authLoading } = useAuthStore();
  const [userId, setUserId] = useState("");
  const [submittedUserId, setSubmittedUserId] = useState<string | null>(null);
  const [activeOnly, setActiveOnly] = useState(true);

  useEffect(() => {
    if (!authLoading && user && user.role !== "ADMIN") {
      router.replace("/dashboard/");
    }
  }, [authLoading, user, router]);

  const listQuery = useQuery({
    queryKey: ["admin-api-keys", submittedUserId, activeOnly],
    queryFn: () => listAdminApiKeys(submittedUserId!, activeOnly),
    enabled: !!submittedUserId,
  });

  const revokeMut = useMutation({
    mutationFn: revokeAdminApiKey,
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: ["admin-api-keys", submittedUserId],
      });
    },
  });

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const id = userId.trim();
    if (!id) return;
    setSubmittedUserId(id);
  };

  if (authLoading || !user) {
    return <p className="text-sm text-secondary-500">Cargando…</p>;
  }
  if (user.role !== "ADMIN") {
    return null;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-white">
          Admin · API keys
        </h1>
        <p className="mt-1 text-sm text-secondary-500">
          Listar y revocar keys de cualquier usuario. Solo metadata (prefix); el
          secret nunca se muestra.
        </p>
      </div>

      <form
        onSubmit={onSearch}
        className="rounded-xl border border-secondary-200 bg-white p-5 space-y-3 dark:border-secondary-700 dark:bg-secondary-900"
      >
        <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary-500">
          Usuario
        </h2>
        <input
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="user_id (UUID)"
          className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm font-mono dark:border-secondary-600 dark:bg-secondary-800"
          required
        />
        <label className="flex items-center gap-2 text-sm text-secondary-600 dark:text-secondary-400">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
            className="rounded border-secondary-300"
          />
          Solo keys activas
        </label>
        <button
          type="submit"
          disabled={!userId.trim()}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          Listar keys
        </button>
      </form>

      {submittedUserId && (
        <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-secondary-500">
            Keys de{" "}
            <span className="font-mono normal-case tracking-normal">
              {submittedUserId}
            </span>{" "}
            ({listQuery.data?.total ?? 0})
          </h2>
          {listQuery.isLoading && (
            <p className="text-sm text-secondary-500">Cargando…</p>
          )}
          {listQuery.isError && (
            <p className="text-sm text-red-600">
              Error al listar keys (¿403 / user_id inválido?).
            </p>
          )}
          <ul className="divide-y divide-secondary-100 dark:divide-secondary-800">
            {(listQuery.data?.items ?? []).map((k) => (
              <li
                key={k.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-secondary-900 dark:text-white">
                    {k.name}{" "}
                    <span className="font-mono text-xs text-secondary-500">
                      {k.prefix}…
                    </span>
                  </p>
                  <p className="text-xs text-secondary-500">
                    {k.is_active ? "Activa" : "Revocada"} · creada{" "}
                    {new Date(k.created_at).toLocaleString()}
                    {k.last_used_at
                      ? ` · último uso ${new Date(k.last_used_at).toLocaleString()}`
                      : ""}
                  </p>
                  {k.description && (
                    <p className="text-xs text-secondary-400">{k.description}</p>
                  )}
                </div>
                {k.is_active && (
                  <button
                    type="button"
                    disabled={revokeMut.isPending}
                    onClick={() => {
                      if (
                        confirm(
                          `¿Revocar key "${k.name}" (${k.prefix}…) del usuario ${submittedUserId}?`
                        )
                      ) {
                        revokeMut.mutate(k.id);
                      }
                    }}
                    className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-400"
                  >
                    Revocar
                  </button>
                )}
              </li>
            ))}
          </ul>
          {listQuery.isSuccess && listQuery.data.total === 0 && (
            <p className="text-sm text-secondary-500">
              Sin keys{activeOnly ? " activas" : ""} para este usuario.
            </p>
          )}
          {revokeMut.isError && (
            <p className="mt-2 text-sm text-red-600">No se pudo revocar.</p>
          )}
        </div>
      )}
    </div>
  );
}
