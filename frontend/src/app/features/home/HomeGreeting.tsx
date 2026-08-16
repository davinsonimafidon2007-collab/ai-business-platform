"use client";

type Props = { name?: string | null };

export function HomeGreeting({ name }: Props) {
  const label = name?.trim() || "there";
  const first = label.split(" ")[0];
  return (
    <div className="mb-4">
      <h1 className="text-2xl font-bold tracking-tight text-secondary-900 dark:text-primary-100">
        ¡Hola, {first}!
      </h1>
      <p className="mt-1 text-sm text-secondary-500 dark:text-secondary-400">
        Resumen de tu actividad
      </p>
    </div>
  );
}
