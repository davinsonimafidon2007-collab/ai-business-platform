import { readFileSync, writeFileSync } from "fs";

const original = readFileSync("frontend/src/app/admin/page.tsx", "utf8");
const lines = original.split(/\r?\n/);
const out = [];
let i = 0;

while (i < lines.length) {
  const line = lines[i];

  if (line === 'import type { AdminSystemStatus } from "@/app/services/adminStatus";') {
    out.push(line);
    out.push('import { fetchHealth } from "@/app/services/health";');
    out.push("function checkTone(value?: string) {");
    out.push("  switch (value) {");
    out.push('    case "ok":');
    out.push('      return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";');
    out.push('    case "degraded":');
    out.push('    case "disabled":');
    out.push('      return "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200";');
    out.push('    case "error":');
    out.push('      return "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";');
    out.push("    default:");
    out.push('      return "bg-secondary-100 text-secondary-700 dark:bg-secondary-700 dark:text-secondary-200";');
    out.push("  }");
    out.push("}");
    i++;
    continue;
  }

  if (line === "  const running = canaryMutation.isPending;") {
    out.push("  const healthQuery = useQuery({");
    out.push('    queryKey: ["health-composite"],');
    out.push("    queryFn: fetchHealth,");
    out.push("    refetchInterval: 30_000,");
    out.push("    retry: 1,");
    out.push("  });");
    out.push(line);
    i++;
    continue;
  }

  if (
    line === '          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">' &&
    lines[i + 1] === '            <div className="mb-3 flex items-center justify-between">' &&
    lines[i + 2] === '              <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary-500">' &&
    lines[i + 3] === "                Provider canary" &&
    lines[i + 4] === "              </h2>"
  ) {
    out.push("          </div>");
    out.push("");
    out.push('          <section className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">');
    out.push('            <div className="flex items-center justify-between gap-2">');
    out.push('              <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">');
    out.push("                Health");
    out.push("              </h2>");
    out.push('              <button');
    out.push('                type="button"');
    out.push('                className="text-xs text-primary-600 hover:underline"');
    out.push("                onClick={() => healthQuery.refetch()}");
    out.push("              >");
    out.push("                Refrescar");
    out.push("              </button>");
    out.push("            </div>");
    out.push("");
    out.push("            {healthQuery.isLoading && (");
    out.push('              <p className="mt-2 text-sm text-secondary-500">Comprobando...</p>');
    out.push("            )}");
    out.push("            {healthQuery.isError && (");
    out.push('              <p className="mt-2 text-sm text-red-600">No se pudo obtener /health</p>');
    out.push("            )}");
    out.push("            {healthQuery.data && (");
    out.push("              <>");
    out.push("                <p className=\"mt-2 text-sm\">");
    out.push("                  Global: { \" }");
    out.push('                  <span');
    out.push('                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${checkTone(');
    out.push('                      healthQuery.data.status === "ok"');
    out.push('                        ? "ok"');
    out.push('                        : healthQuery.data.status === "degraded"');
    out.push('                          ? "degraded"');
    out.push('                          : "error"');
    out.push("                    )}`}");
    out.push("                  >");
    out.push("                    {healthQuery.data.status}");
    out.push("                  </span>");
    out.push('                  <span className="ml-2 text-xs text-secondary-500">');
    out.push("                    v{healthQuery.data.version}");
    out.push("                  </span>");
    out.push("                </p>");
    out.push('                <ul className="mt-3 flex flex-wrap gap-2">');
    out.push('                  {(["api", "database", "redis"] as const).map((key) => (');
    out.push('                    <li');
    out.push('                      key={key}');
  if (line === '            onClick={() => queryClient.invalidateQueries({ queryKey: ["admin-status"] })}') {
    out.push("            onClick={() => {");
    out.push('              queryClient.invalidateQueries({ queryKey: ["admin-status"] });');
    out.push('              queryClient.invalidateQueries({ queryKey: ["health-composite"] });');
    out.push("            }}");
    i++;
    continue;
  }

  out.push(line);
  i++;
}

const result = out.join("\n");
writeFileSync("frontend/src/app/admin/page.tsx", result);
console.log("done");

    out.push('                      className={`rounded-full px-3 py-1 text-xs font-medium ${checkTone(');
    out.push("                        healthQuery.data.checks?.[key]");
    out.push("                      )}`}");
    out.push("                    >");
    out.push('                      {key}: {healthQuery.data.checks?.[key] ?? "—"}');
    out.push("                    </li>");
    out.push("                  ))}");
    out.push("                </ul>");
    out.push("                {(healthQuery.data.providers?.length ?? 0) > 0 && (");
    out.push('                  <p className="mt-2 text-xs text-secondary-500">');
    out.push("                    Providers en health: {healthQuery.data.providers.join(", ")}");
    out.push("                  </p>");
    out.push("                )}");
    out.push("              </>");
    out.push("            )}");
    out.push("          </section>");
    out.push("");
    out.push('          <div className="rounded-xl border border-secondary-200 bg-white p-5 dark:border-secondary-700 dark:bg-secondary-900">');
    out.push('            <div className="mb-3 flex items-center justify-between">');
    out.push('              <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary-500">');
    out.push("                Provider canary");
    out.push("              </h2>");
    i += 5;
    continue;
  }

