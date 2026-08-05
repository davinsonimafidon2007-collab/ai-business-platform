"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchAdminStatus,
  runProviderCanary,
} from "@/app/services/adminStatus";
import type { AdminSystemStatus } from "@/app/services/adminStatus";

function Badge({
  ok,
  label,
}: {
  ok: boolean | null | undefined;
  label: string;
}) {
  const color =
    ok === true
      ? "bg-green-100 text-green-800"
      : ok === false
        ? "bg-red-100 text-red-800"
        : "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {label}
    </span>
  );
}

function getStatusCode(err: unknown): number | undefined {
  return (err as { response?: { status?: number } })?.response?.status;
}

export default function AdminStatusPage() {
  const queryClient = useQueryClient();

  const {
    data: status,
    isLoading: loading,
    error: queryError,
  } = useQuery({
    queryKey: ["admin-status"],
    queryFn: fetchAdminStatus,
  });

  const canaryMutation = useMutation({
    mutationFn: runProviderCanary,
    onSuccess: (data: AdminSystemStatus) => {
      queryClient.setQueryData(["admin-status"], data);
    },
  });

  const running = canaryMutation.isPending;

  const error = queryError
    ? getStatusCode(queryError) === 403
      ? "Solo administradores pueden ver este panel."
      : getStatusCode(queryError) === 401
        ? "Sesión expirada. Vuelve a iniciar sesión."
        : "No se pudo cargar el estado del sistema."
    : canaryMutation.error
      ? getStatusCode(canaryMutation.error) === 403
        ? "Solo administradores pueden ejecutar el canary."
        : "Error al ejecutar el canary. Revisa logs del API."
      : null;

  const canary = status?.canary;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-white">
            Admin · Sistema
          </h1>
          <p className="mt-1 text-sm text-secondary-500">
            Redis y último canary de providers (AS24 / mobile.de)
          </p>
        </div>
        <button
          type="button"
          onClick={() => canaryMutation.mutate()}
          disabled={running || loading}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {running ? "Ejecutando canary…" : "Run canary"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading && !status ? (
        <p className="text-sm text-secondary-500">Cargando…</p>
      ) : status ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-secondary-500">
              Infra
            </h2>
            <div className="flex items-center gap-3">
              <span className="text-sm text-secondary-700 dark:text-secondary-300">Redis</span>
              <Badge
                ok={status.redis_ok}
                label={
                  status.redis_ok === true
                    ? "OK"
                    : status.redis_ok === false
                      ? "DOWN"
                      : "N/A"
                }
              />
            </div>
          </div>

          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary-500">
                Provider canary
              </h2>
              <Badge
                ok={canary?.success}
                label={
                  canary?.success === true
                    ? "PASS"
                    : canary?.success === false
                      ? "FAIL"
                      : "SIN DATOS"
                }
              />
            </div>
            <dl className="grid gap-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-secondary-500">Finished at</dt>
                <dd className="font-mono text-secondary-800 dark:text-secondary-200">
                  {canary?.finished_at ?? "—"}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-secondary-500">Message</dt>
                <dd className="text-right text-secondary-800 dark:text-secondary-200">
                  {canary?.message ?? "—"}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-secondary-500">mobile_status</dt>
                <dd className="font-mono">{canary?.mobile_status ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-secondary-500">strict_mobile</dt>
                <dd className="font-mono">
                  {canary?.strict_mobile == null ? "—" : String(canary.strict_mobile)}
                </dd>
              </div>
            </dl>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <pre className="overflow-auto rounded-lg bg-secondary-50 p-3 text-xs dark:bg-secondary-800">
                {JSON.stringify(canary?.autoscout24 ?? null, null, 2)}
              </pre>
              <pre className="overflow-auto rounded-lg bg-secondary-50 p-3 text-xs dark:bg-secondary-800">
                {JSON.stringify(canary?.mobile_de ?? null, null, 2)}
              </pre>
            </div>
          </div>

          <button
            type="button"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["admin-status"] })}
            className="text-sm text-primary-600 hover:underline"
          >
            Refrescar snapshot
          </button>
        </div>
      ) : null}
    </div>
  );
}