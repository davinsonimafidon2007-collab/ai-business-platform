"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiKeyCreated,
  createApiKey,
  listApiKeys,
  revokeApiKey,
} from "@/app/services/apiKeys";

export default function ApiKeysPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [createdOnce, setCreatedOnce] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const listQuery = useQuery({
    queryKey: ["api-keys"],
    queryFn: listApiKeys,
  });

  const createMut = useMutation({
    mutationFn: createApiKey,
    onSuccess: (data) => {
      setCreatedOnce(data);
      setName("");
      setDescription("");
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const revokeMut = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const onCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    createMut.mutate({
      name: name.trim(),
      description: description.trim() || null,
    });
  };

  const copyKey = async () => {
    if (!createdOnce?.api_key) return;
    await navigator.clipboard.writeText(createdOnce.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-white">
          API keys
        </h1>
        <p className="mt-1 text-sm text-secondary-500">
          Keys para autenticar integraciones. La clave completa solo se muestra al crearla.
        </p>
      </div>

      {/* Banner key recién creada */}
      {createdOnce && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950/40">
          <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
            Guarda esta key ahora — no se volverá a mostrar
          </p>
          <code className="mt-2 block break-all rounded bg-white/80 p-2 text-xs dark:bg-secondary-900">
            {createdOnce.api_key}
          </code>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => void copyKey()}
              className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
            >
              {copied ? "Copiada" : "Copiar"}
            </button>
            <button
              type="button"
              onClick={() => setCreatedOnce(null)}
              className="text-xs text-amber-800 underline dark:text-amber-300"
            >
              Cerrar
            </button>
          </div>
        </div>
      )}

      {/* Crear */}
      <form
        onSubmit={onCreate}
        className="rounded-xl border border-secondary-200 bg-white p-5 space-y-3 dark:border-secondary-700 dark:bg-secondary-900"
      >
        <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary-500">
          Nueva key
        </h2>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nombre (ej. script-import)"
          className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm dark:border-secondary-600 dark:bg-secondary-800"
          required
          maxLength={255}
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Descripción (opcional)"
          className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm dark:border-secondary-600 dark:bg-secondary-800"
          maxLength={2000}
        />
        <button
          type="submit"
          disabled={createMut.isPending || !name.trim()}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          {createMut.isPending ? "Creando…" : "Crear API key"}
        </button>
        {createMut.isError && (
          <p className="text-sm text-red-600">No se pudo crear la key.</p>
        )}
      </form>

      {/* Lista */}
      <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-secondary-500">
          Tus keys ({listQuery.data?.total ?? 0})
        </h2>
        {listQuery.isLoading && (
          <p className="text-sm text-secondary-500">Cargando…</p>
        )}
        {listQuery.isError && (
          <p className="text-sm text-red-600">Error al listar keys.</p>
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
              </div>
              {k.is_active && (
                <button
                  type="button"
                  disabled={revokeMut.isPending}
                  onClick={() => {
                    if (confirm(`¿Revocar key "${k.name}"?`)) {
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
        {listQuery.data?.total === 0 && (
          <p className="text-sm text-secondary-500">Aún no tienes API keys.</p>
        )}
      </div>
    </div>
  );
}