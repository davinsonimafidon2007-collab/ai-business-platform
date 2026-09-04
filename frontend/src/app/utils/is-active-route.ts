/**
 * Compara `pathname` contra el `href` de un enlace de navegación para saber
 * si debe marcarse como activo.
 *
 * Bug real: todos los `href` de navegación llevan barra final ("/dashboard/")
 * para que funcionen en el build nativo de Capacitor (`trailingSlash: true`
 * ahí). En el build de servidor/Docker (lo que sirve la web real)
 * `trailingSlash` NO está activo, así que `pathname` nunca lleva barra
 * final — la comparación directa contra `href` nunca coincidía y ningún
 * item de navegación se marcaba como activo en ningún sitio de la app.
 * Normaliza quitando la barra final de ambos lados antes de comparar.
 */
export function isActiveRoute(pathname: string, href: string): boolean {
  const normalize = (p: string) => (p.length > 1 ? p.replace(/\/+$/, "") : p);
  const current = normalize(pathname);
  const target = normalize(href);
  return current === target || current.startsWith(`${target}/`);
}
