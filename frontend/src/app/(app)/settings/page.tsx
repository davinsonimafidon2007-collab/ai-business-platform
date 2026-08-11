"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/app/components/ui/button";
import { getApiBaseUrl, setApiBaseUrl } from "@/app/config/api-url";

export default function SettingsPage() {
  const router = useRouter();
  const [url, setUrl] = useState(getApiBaseUrl());
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = () => {
    const clean = url.trim().replace(/\/+$/, "");
    if (!/^https?:\/\/.+/.test(clean)) {
      setError("Introduce una URL válida (ej. http://192.168.1.50:8000)");
      return;
    }
    setApiBaseUrl(clean);
    setError(null);
    setSaved(true);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
          Configuración
        </h1>
        <p className="text-secondary-500 dark:text-secondary-400">
          Conexión con el backend
        </p>
      </div>

      <div className="rounded-lg border border-secondary-200 bg-white p-6 dark:border-secondary-700 dark:bg-secondary-800">
        <h2 className="text-base font-semibold text-secondary-900 dark:text-secondary-100">
          Dirección de la API
        </h2>
        <p className="mt-1 text-sm text-secondary-500 dark:text-secondary-400">
          Si estás en un móvil físico, usa la IP LAN del PC donde corre el
          backend (ej. <code className="rounded bg-secondary-100 px-1 dark:bg-secondary-700">http://192.168.1.50:8000</code>).
          La IP se averigua con <code className="rounded bg-secondary-100 px-1 dark:bg-secondary-700">ipconfig</code>.
        </p>

        <div className="mt-4 space-y-3">
          <input
            type="text"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setSaved(false);
            }}
            placeholder="http://192.168.1.50:8000"
            className="block w-full rounded-lg border border-secondary-300 bg-white px-3 py-2 text-sm text-secondary-900 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-900 dark:text-secondary-100"
          />
          {error && (
            <p className="text-sm font-medium text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
          {saved && (
            <p className="text-sm font-medium text-green-600 dark:text-green-400">
              Guardado. Reinicia la app para aplicar el cambio.
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleSave}>Guardar</Button>
            <Button
              variant="outline"
              onClick={() => {
                window.localStorage.removeItem("api_base_url");
                setUrl(getApiBaseUrl());
                setSaved(true);
              }}
            >
              Restablecer
            </Button>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-secondary-200 bg-white p-6 dark:border-secondary-700 dark:bg-secondary-800">
        <h2 className="text-base font-semibold text-secondary-900 dark:text-secondary-100">
          Guía rápida
        </h2>
        <ol className="mt-3 list-inside list-decimal space-y-1 text-sm text-secondary-600 dark:text-secondary-400">
          <li>Conecta el PC y el móvil a la misma red Wi-Fi.</li>
          <li>Arranca el backend en el PC (debe escuchar en 0.0.0.0:8000).</li>
          <li>Averigua la IP LAN del PC con <code className="rounded bg-secondary-100 px-1 dark:bg-secondary-700">ipconfig</code>.</li>
          <li>Introduce aquí <code className="rounded bg-secondary-100 px-1 dark:bg-secondary-700">http://IP:8000</code> y guarda.</li>
          <li>Reinicia la app.</li>
        </ol>
      </div>

      <Link href="/dashboard" className="inline-block text-sm text-primary-600 hover:underline dark:text-primary-400">
        ← Volver al inicio
      </Link>
    </div>
  );
}
