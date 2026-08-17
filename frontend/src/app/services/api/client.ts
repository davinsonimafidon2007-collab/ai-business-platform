import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";
import { isAuthDisabled } from "@/app/config/app-mode";
import { getApiBaseUrl } from "@/app/config/api-url";
import { secureStorage } from "@/app/services/storage";
import { TOKEN_KEYS } from "@/app/store/auth-store";

const API_BASE_URL = getApiBaseUrl();

// P6: retry con backoff exponencial + jitter para fallos transitorios
// (errores de red/timeout, 429, 5xx). Solo peticiones idempotentes.
const RETRY_MAX_ATTEMPTS = 2; // reintentos adicionales (máx. 3 intentos totales)
const RETRY_BASE_DELAY_MS = 500;
const RETRY_MAX_DELAY_MS = 4000;

const RETRYABLE_METHODS = new Set(["get", "head", "delete", "options"]);

class ApiClient {
  private client: AxiosInstance;
  private refreshPromise: Promise<string | null> | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 30000,
    });

    this.client.interceptors.request.use(this.handleRequest.bind(this));
    this.client.interceptors.response.use(
      (response) => response,
      this.handleError.bind(this)
    );
  }

  private async handleRequest(
    config: InternalAxiosRequestConfig
  ): Promise<InternalAxiosRequestConfig> {
    const token = await secureStorage.get(TOKEN_KEYS.accessToken);
    // Protección básica: solo enviar si el token existe y parece válido
    if (token && token.trim().length > 10) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  }

  private isRetryable(error: AxiosError): boolean {
    // Sin respuesta → error de red/timeout (transitorio por definición).
    if (!error.response) {
      return true;
    }
    const status = error.response.status;
    // 401 se gestiona con el refresh (abajo); el resto de 4xx no se reintenta.
    return status === 429 || status >= 500;
  }

  private async retryDelay(error: AxiosError, attempt: number): Promise<void> {
    // Backoff exponencial con full jitter: delay en [0, base*2^attempt).
    let delay = Math.floor(
      Math.random() * RETRY_BASE_DELAY_MS * Math.pow(2, attempt)
    );
    // Respetar Retry-After de 429 (formato segundos) si viene.
    const retryAfter = error.response?.headers?.["retry-after"];
    if (error.response?.status === 429 && retryAfter) {
      const secs = Number.parseInt(String(retryAfter), 10);
      if (!Number.isNaN(secs)) {
        delay = Math.max(delay, secs * 1000);
      }
    }
    await new Promise((resolve) =>
      setTimeout(resolve, Math.min(delay, RETRY_MAX_DELAY_MS))
    );
  }

  private async handleError(error: AxiosError): Promise<never> {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
      _retryCount?: number;
    };

    if (originalRequest) {
      // P6: reintentar fallos transitorios (red/timeout, 429, 5xx) en métodos
      // idempotentes. No reintentar 401 (lo gestiona el refresh más abajo).
      const method = (originalRequest.method ?? "get").toLowerCase();
      const retryCount = originalRequest._retryCount ?? 0;
      if (
        RETRYABLE_METHODS.has(method) &&
        error.response?.status !== 401 &&
        this.isRetryable(error) &&
        retryCount < RETRY_MAX_ATTEMPTS
      ) {
        originalRequest._retryCount = retryCount + 1;
        await this.retryDelay(error, retryCount);
        return this.client(originalRequest);
      }
    }

    // Auth desactivada (uso personal): no hay sesión que refrescar ni a la que
    // redirigir. No entrar en el loop de 401 → logout → login.
    if (isAuthDisabled()) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const newToken = await this.refreshAccessToken();
        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return this.client(originalRequest);
        }
      } catch {
        // Refresco fallido → naufrageo la sesión igual que logout pero SIN
        // importar el store (evitaría dependencia circular). Estrategia elegida:
        // clearTokens() + evento "auth:logout" que el provider escucha para
        // resetear el store y vaciar el caché de React Query.
        await this.clearTokens();
        if (typeof window !== "undefined") {
          window.dispatchEvent(new Event("auth:logout"));
          window.location.href = "/auth/login/";
        }
      }
    }

    return Promise.reject(error);
  }

  private async refreshAccessToken(): Promise<string | null> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = new Promise(async (resolve) => {
      try {
        const refreshToken = await secureStorage.get(TOKEN_KEYS.refreshToken);
        if (!refreshToken) {
          resolve(null);
          return;
        }

        const response = await axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;
        await secureStorage.set(TOKEN_KEYS.accessToken, access_token);
        await secureStorage.set(TOKEN_KEYS.refreshToken, newRefreshToken);
        resolve(access_token);
      } catch {
        resolve(null);
      } finally {
        this.refreshPromise = null;
      }
    });

    return this.refreshPromise;
  }

  private async clearTokens(): Promise<void> {
    await secureStorage.remove(TOKEN_KEYS.accessToken);
    await secureStorage.remove(TOKEN_KEYS.refreshToken);
    await secureStorage.remove(TOKEN_KEYS.user);
  }

  get axiosInstance(): AxiosInstance {
    return this.client;
  }
}

export const apiClient = new ApiClient();
export const api = apiClient.axiosInstance;