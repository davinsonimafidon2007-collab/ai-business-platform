"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchAdminStatus,
  runProviderCanary,
} from "@/app/services/adminStatus";
import type { AdminSystemStatus } from "@/app/services/adminStatus";
import { fetchAdminMetrics } from "@/app/services/adminMetrics";
import {
  createFeatureFlag,
  deleteFeatureFlag,
  fetchFeatureFlags,
  updateFeatureFlag,
} from "@/app/services/featureFlags";
import { fetchHealth } from "@/app/services/health";

function checkTone(value?: string) {
  switch (value) {
    case "ok":
      return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
    case "degraded":
    case "disabled":
      return "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200";
    case "error":
      return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
    default:
      return "bg-secondary-100 text-secondary-700 dark:bg-secondary-700 dark:text-secondary-200";
  }
}


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

  const flagsQuery = useQuery({
    queryKey: ["feature-flags"],
    queryFn: fetchFeatureFlags,
  });

  const ttlFlagsMutation = useMutation({
    mutationFn: updateFeatureFlag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feature-flags"] });
    },
  });

  const createFlagMutation = useMutation({
    mutationFn: createFeatureFlag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feature-flags"] });
    },
  });

  const deleteFlagMutation = useMutation({
    mutationFn: deleteFeatureFlag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feature-flags"] });
    },
  });

  const metricsQuery = useQuery({
    queryKey: ["admin-metrics"],
    queryFn: fetchAdminMetrics,
    refetchInterval: 15_000,
    retry: 1,
  });

    const healthQuery = useQuery({
    queryKey: ["health-composite"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
    retry: 1,
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

          <section className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">
                Health
              </h2>
              <button
                type="button"
                className="text-xs text-primary-600 hover:underline"
                onClick={() => healthQuery.refetch()}
              >
                Refrescar
              </button>
            </div>

            {healthQuery.isLoading && (
              <p className="mt-2 text-sm text-secondary-500">Comprobando...</p>
            )}
            {healthQuery.isError && (
              <p className="mt-2 text-sm text-red-600">No se pudo obtener /health</p>
            )}
            {healthQuery.data && (
              <>
                <p className="mt-2 text-sm">
                  Global: {" "}
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${checkTone(
                      healthQuery.data.status === "ok"
                        ? "ok"
                        : healthQuery.data.status === "degraded"
                          ? "degraded"
                          : "error"
                    )}`}
                  >
                    {healthQuery.data.status}
                  </span>
                  <span className="ml-2 text-xs text-secondary-500">
                    v{healthQuery.data.version}
                  </span>
                </p>
                <ul className="mt-3 flex flex-wrap gap-2">
                  {(["api", "database", "redis"] as const).map((key) => (
                    <li
                      key={key}
                      className={`rounded-full px-3 py-1 text-xs font-medium ${checkTone(
                        healthQuery.data.checks?.[key]
                      )}`}
                    >
                      {key}: {healthQuery.data.checks?.[key] ?? "—"}
                    </li>
                  ))}
                </ul>
                {(healthQuery.data.providers?.length ?? 0) > 0 && (
                  <p className="mt-2 text-xs text-secondary-500">
                    Providers en health: {healthQuery.data.providers.join(", ")}
                  </p>
                )}
              </>
            )}
          </section>

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

          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-secondary-500">
              Feature flags
            </h2>
            {flagsQuery.isLoading && (
              <p className="text-sm text-secondary-500">Cargando flags…</p>
            )}
            {flagsQuery.isError && (
              <p className="text-sm text-red-500">
                No se pudieron cargar los feature flags.
              </p>
            )}
            {flagsQuery.data && (
              <div className="space-y-2">
                {flagsQuery.data.map((flag) => (
                  <div
                    key={flag.id}
                    className="flex items-center justify-between gap-4 rounded-lg bg-secondary-50 px-3 py-2 dark:bg-secondary-800"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-mono text-sm text-secondary-900 dark:text-white">
                        {flag.key}
                      </div>
                      {flag.description && (
                        <div className="truncate text-xs text-secondary-500">
                          {flag.description}
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        ttlFlagsMutation.mutate({
                          key: flag.key,
                          value: !flag.value,
                        })
                      }
                      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
                        flag.value
                          ? "bg-green-500"
                          : "bg-secondary-300 dark:bg-secondary-700"
                      }`}
                      aria-label={`Toggle ${flag.key}`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          flag.value ? "translate-x-6" : "translate-x-1"
                        }`}
                      />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (window.confirm(`Eliminar flag "${flag.key}"?`)) {
                          deleteFlagMutation.mutate(flag.key);
                        }
                      }}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Eliminar
                    </button>
                  </div>
                ))}
                <div className="mt-3">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const data = new FormData(e.currentTarget);
                      const key = String(data.get("key") ?? "").trim();
                      if (!key) {
                        return;
                      }
                      createFlagMutation.mutate({
                        key,
                        description: String(data.get("description") ?? "").trim() || null,
                      });
                      e.currentTarget.reset();
                    }}
                    className="flex flex-wrap items-center gap-2"
                  >
                    <input
                      name="key"
                      required
                      placeholder="nueva_flag (snake_case)"
                      className="flex-1 rounded-lg border border-secondary-200 bg-white px-3 py-1.5 text-sm dark:border-secondary-700 dark:bg-secondary-800"
                    />
                    <input
                      name="description"
                      placeholder="Descripción"
                      className="flex-1 rounded-lg border border-secondary-200 bg-white px-3 py-1.5 text-sm dark:border-secondary-700 dark:bg-secondary-800"
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
                    >
                      Crear
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary-500">
                Métricas de negocio (Prometheus)
              </h2>
              <button
                type="button"
                className="text-xs text-primary-600 hover:underline"
                onClick={() => metricsQuery.refetch()}
              >
                Refrescar
              </button>
            </div>
            {metricsQuery.isLoading && (
              <p className="text-sm text-secondary-500">Cargando métricas…</p>
            )}
            {metricsQuery.isError && (
              <p className="text-sm text-red-500">
                No se pudieron cargar las métricas.
              </p>
            )}
            {metricsQuery.data && (
              <pre className="overflow-auto rounded-lg bg-secondary-50 p-3 text-xs dark:bg-secondary-800">
                {metricsQuery.data}
              </pre>
            )}
          </div>

          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-secondary-500">
              Jobs ({status.jobs.length})
            </h2>
            {status.jobs.length === 0 ? (
              <p className="text-sm text-secondary-500">
                Sin jobs registrados (scheduler desactivado o sin configurar).
              </p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-secondary-200 text-secondary-500 dark:border-secondary-700">
                    <th className="py-2 pr-3 font-medium">Job</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 pr-3 font-medium">OK / Fail</th>
                    <th className="py-2 pr-3 font-medium">Racha</th>
                    <th className="py-2 font-medium">Last run</th>
                  </tr>
                </thead>
                <tbody>
                  {status.jobs.map((job) => (
                    <tr
                      key={job.name}
                      className="border-b border-secondary-100 last:border-0 dark:border-secondary-800"
                    >
                      <td className="py-2 pr-3 font-medium text-secondary-900 dark:text-white">
                        {job.name}
                      </td>
                      <td className="py-2 pr-3">
                        <Badge
                          ok={
                            job.status === "success"
                              ? true
                              : job.status === "failed"
                                ? false
                                : null
                          }
                          label={job.status}
                        />
                      </td>
                      <td className="py-2 pr-3 font-mono text-secondary-700 dark:text-secondary-300">
                        {job.success_count} / {job.failure_count}
                      </td>
                      <td className="py-2 pr-3">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            job.consecutive_failures >= 3
                              ? "bg-red-100 text-red-800"
                              : job.consecutive_failures > 0
                                ? "bg-amber-100 text-amber-800"
                                : "bg-green-100 text-green-800"
                          }`}
                        >
                          {job.consecutive_failures}
                        </span>
                      </td>
                      <td className="py-2 font-mono text-secondary-700 dark:text-secondary-300">
                        {job.last_execution ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-secondary-500">
              Providers (comparables)
            </h2>
            <p className="text-sm text-secondary-700 dark:text-secondary-300">
              Perfil importación:{" "}
              <span className="font-medium text-secondary-900 dark:text-white">
                {status.providers.default_import_cost_profile ?? "—"}
              </span>
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {(status.providers.providers ?? []).map((name) => (
                <li
                  key={name}
                  className="rounded-full bg-secondary-100 px-3 py-1 text-xs font-medium text-secondary-800 dark:bg-secondary-700 dark:text-secondary-100"
                >
                  {name}
                </li>
              ))}
            </ul>
            {(status.providers.providers ?? []).length === 0 && (
              <p className="mt-2 text-sm text-amber-600">
                Ningún provider en registry
              </p>
            )}
            <div className="mt-3 grid grid-cols-1 gap-1 text-xs text-secondary-600 dark:text-secondary-400 sm:grid-cols-3">
              <span>
                ES fixture: {String(status.providers.enable_es_market_fixture)}
              </span>
              <span>
                Coches.net fixture:{" "}
                {String(status.providers.enable_coches_net_fixture)}
              </span>
              <span>
                AS24 ES: {String(status.providers.enable_autoscout24_es)}
              </span>
            </div>
            <p className="mt-2 text-xs text-secondary-500">
              Con perfil SPAIN/ES los fixtures offline pueden auto-registrarse
              aunque el flag esté en false (DEST.1).
            </p>
          </div>

          <button
            type="button"
                                    onClick={() => {
              queryClient.invalidateQueries({ queryKey: ["admin-status"] });
              queryClient.invalidateQueries({ queryKey: ["health-composite"] });
            }}
            className="text-sm text-primary-600 hover:underline"
          >
            Refrescar snapshot
          </button>
        </div>
      ) : null}
    </div>
  );
}