import { Capacitor } from "@capacitor/core";
import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";
import { isAuthDisabled } from "@/app/config/app-mode";

// Detecta el protocolo desde la variable de entorno o desde el contexto del navegador
// para evitar errores de Mixed Content en Android/WebView
const getApiBaseUrl = (): string => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;

  if (envUrl) {
    return envUrl;
  }

  // En Android nativo (Capacitor WebView) sin NEXT_PUBLIC_API_URL, el emulador
  // expone el host en 10.0.2.2. El network_security_config ya permite cleartext
  // a ese host en desarrollo (evita generar un https://localhost:8000 inválido).
  if (Capacitor.isNativePlatform() && Capacitor.getPlatform() === "android") {
    return "http://10.0.2.2:8000";
  }

  // En desarrollo, usar el mismo protocolo que la página actual
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const port = window.location.port;

    if (host === "localhost" || host === "127.0.0.1") {
      return `${protocol}//${host}:8000`;
    }
  }

  // Fallback para desarrollo local
  return "http://localhost:8000";
};

const API_BASE_URL = getApiBaseUrl();

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

  private handleRequest(
    config: InternalAxiosRequestConfig
  ): InternalAxiosRequestConfig {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      // Protección básica: solo enviar si el token existe y parece válido
      if (token && token.trim().length > 10) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  }

  private async handleError(error: AxiosError): Promise<never> {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

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
        this.clearTokens();
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
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) {
          resolve(null);
          return;
        }

        const response = await axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", newRefreshToken);
        resolve(access_token);
      } catch {
        resolve(null);
      } finally {
        this.refreshPromise = null;
      }
    });

    return this.refreshPromise;
  }

  private clearTokens(): void {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }

  get axiosInstance(): AxiosInstance {
    return this.client;
  }
}

export const apiClient = new ApiClient();
export const api = apiClient.axiosInstance;