export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8">
      <main className="flex flex-col items-center gap-8">
        <h1 className="text-4xl font-bold text-primary-600 dark:text-primary-400">
          AI Business Platform
        </h1>
        <p className="text-lg text-secondary-600 dark:text-secondary-400 text-center max-w-md">
          Vehicle import analysis and market intelligence platform
        </p>
        <div className="flex gap-4">
          <a
            href="/auth/login"
            className="rounded-lg bg-primary-600 px-6 py-3 text-white font-medium hover:bg-primary-700 transition-colors"
          >
            Iniciar Sesión
          </a>
          <a
            href="/auth/register"
            className="rounded-lg border border-primary-600 px-6 py-3 text-primary-600 font-medium hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
          >
            Registrarse
          </a>
        </div>
      </main>
    </div>
  );
}