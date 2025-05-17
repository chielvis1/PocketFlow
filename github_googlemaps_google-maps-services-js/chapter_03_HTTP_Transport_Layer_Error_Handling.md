# Chapter 3: HTTP Transport Layer & Error Handling  

# Chapter 3: HTTP Transport Layer & Error Handling

## Introduction

In this chapter, we’ll dig into `src/adapter.ts`, the HTTP abstraction layer at the heart of our client. You’ll learn:

- How we configure an Axios instance for logging and retry/backoff  
- The generic `adapter.request<T>()` method that dispatches and parses requests  
- How we centralize error normalization into an `ApiError` wrapper  

By the end, you’ll understand how every Maps API call flows through this layer, and how failures become consistent, typed exceptions.

---

## 3.1 Configuring Axios

### 3.1.1 Creating the Axios Instance

We start by creating a single Axios instance that all requests share:

```ts
// src/adapter.ts
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const DEFAULT_TIMEOUT = 10_000; // in ms
const BASE_URL = 'https://maps.googleapis.com/maps/api';

function createAxiosInstance(): AxiosInstance {
  return axios.create({
    baseURL: BASE_URL,
    timeout: DEFAULT_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

const axiosInstance = createAxiosInstance();
```

### 3.1.2 Interceptors: Logging & Retry/Backoff

#### Logging Interceptor

We attach request and response interceptors for structured logging:

```ts
axiosInstance.interceptors.request.use((config) => {
  console.debug(`[HTTP ▶] ${config.method?.toUpperCase()} ${config.url}`, {
    params: config.params,
    data: config.data,
  });
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => {
    console.debug(
      `[HTTP ◀] ${response.status} ${response.config.url}`,
      response.data
    );
    return response;
  },
  (error) => Promise.reject(error)
);
```

#### Retry/Backoff Interceptor

A simple exponential backoff retry strategy lets us gracefully recover from transient failures:

```ts
const MAX_RETRIES = 3;

axiosInstance.interceptors.response.use(undefined, async (error) => {
  const config = error.config as AxiosRequestConfig & { __retryCount?: number };

  config.__retryCount = config.__retryCount || 0;
  if (config.__retryCount < MAX_RETRIES) {
    config.__retryCount += 1;
    const delay = 2 ** (config.__retryCount - 1) * 100; // 100ms, 200ms, 400ms
    await new Promise((resolve) => setTimeout(resolve, delay));
    return axiosInstance.request(config);
  }

  return Promise.reject(error);
});
```

---

## 3.2 The Generic `adapter.request<T>()` Method

Rather than calling Axios directly, higher-level services use a generic request method:

```ts
export class Adapter {
  private client: AxiosInstance;

  constructor(client: AxiosInstance = axiosInstance) {
    this.client = client;
  }

  async request<T>(config: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.client.request<T>(config);
      return response.data;
    } catch (err) {
      throw ApiError.from(err);
    }
  }
}
```

### How It Works

1. **Type Safety**  
   The `<T>` generic ensures the caller gets the right shape back.  
2. **Single Dispatch Point**  
   All HTTP calls—GET, POST, etc.—flow through `Adapter.request`.  
3. **Error Normalization**  
   Any thrown error is passed to `ApiError.from()`, our central error factory.

---

## 3.3 Centralized Error Handling with `ApiError`

Rather than littering our code with ad-hoc error checks, we wrap all failures into an `ApiError` class.

### 3.3.1 The `ApiError` Class

```ts
// src/errors/ApiError.ts
import { AxiosError } from 'axios';

export class ApiError extends Error {
  public status?: number;
  public data?: any;

  private constructor(message: string, status?: number, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  static from(error: unknown): ApiError {
    // Axios errors (network, non-2xx, timeouts)
    if ((error as AxiosError).isAxiosError) {
      const axiosError = error as AxiosError;
      const status = axiosError.response?.status;
      const data = axiosError.response?.data;
      return new ApiError(
        `HTTP ${status} – ${axiosError.message}`,
        status,
        data
      );
    }

    // JSON parse errors or other runtime errors
    if (error instanceof SyntaxError) {
      return new ApiError(`JSON parse error: ${error.message}`);
    }

    // Fallback
    return new ApiError(`Unknown error: ${String(error)}`);
  }
}
```

### 3.3.2 Error Flow

- **Network / timeout** → Axios throws → `ApiError.from()` captures status `undefined` or `ECONNABORTED`.  
- **4xx / 5xx** → Axios rejects with `response` → we extract `status` and `data`.  
- **Invalid JSON** → thrown by our JSON parser (rare with Axios, but possible in transforms) → wrapped as `SyntaxError`.  
- **Other** → generic message.

---

## 3.4 Putting It All Together

Here’s how a service calls the adapter:

```ts
// src/services/GeocodingService.ts
import { Adapter } from '../adapter';
import { GeocodeResponse } from '../types';

export class GeocodingService {
  private adapter = new Adapter();

  async geocode(address: string): Promise<GeocodeResponse> {
    try {
      return await this.adapter.request<GeocodeResponse>({
        method: 'GET',
        url: '/geocode/json',
        params: { address },
      });
    } catch (err) {
      // err is guaranteed to be an ApiError
      console.error('Geocoding failed:', err);
      throw err; // or wrap further
    }
  }
}
```

- The service never touches Axios directly.  
- Errors bubbling up are always `ApiError` instances with `status` and `data`.  
- Any log, retry, timeout is handled once in `adapter.ts`.

---

## Conclusion

In this chapter, you saw how our HTTP transport layer—centered on `src/adapter.ts`:

1. **Configures** a single, shared Axios instance with logging and retry/backoff.  
2. **Dispatches** typed requests via the generic `adapter.request<T>()` method.  
3. **Normalizes** all failures into a consistent `ApiError` shape.

This clean separation means all higher-level API services stay focused on business logic, confident that network concerns and error handling are solved in one place. In the next chapter, we’ll explore how we assemble these services into the public `createClient()` factory.