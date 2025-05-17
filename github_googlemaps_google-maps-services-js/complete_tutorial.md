# Tutorial - English

## Table of Contents

1. [Introduction & Project Overview  ](chapter_01_Introduction_Project_Overview.md)
2. [Client Configuration & Factory Wiring  ](chapter_02_Client_Configuration_Factory_Wiring.md)
3. [HTTP Transport Layer & Error Handling  ](chapter_03_HTTP_Transport_Layer_Error_Handling.md)
4. [Parameter Utilities & Serialization  ](chapter_04_Parameter_Utilities_Serialization.md)
5. [Service Modules & Domain Models  ](chapter_05_Service_Modules_Domain_Models.md)
6. [Making API Calls: End-to-End Flow  ](chapter_06_Making_API_Calls_End-to-End_Flow.md)
7. [Testing, Documentation & Release Workflow  ](chapter_07_Testing_Documentation_Release_Workflow.md)


---

# Chapter 1: Introduction & Project Overview  

# Chapter 1: Introduction & Project Overview

Welcome to the first chapter of our tutorial for the Google Maps TypeScript-first REST client. In this chapter, you’ll learn:

1. Why this library exists and how it’s organized  
2. How to install it and make your very first API call  
3. The high-level abstractions and folder layout you’ll encounter  

---

## 1.1 Introduction

Modern web apps often need to integrate with Google Maps services—geocoding addresses, calculating routes, looking up time zones, and more. This library aims to be:

- **Thin**: Minimal overhead on top of Google’s REST endpoints  
- **TypeScript-First**: Fully typed request and response objects  
- **Flexible**: Support for all Google Maps web services via a single `createClient()` factory  

Whether you’re building a server-side renderer, a Next.js app, or simply scripting batch geocoding jobs, this client gives you first-class TypeScript support without reinventing HTTP plumbing.

---

## 1.2 Key Concepts & Architecture

Before diving into code, let’s map out the core ideas you’ll see in this repository.

### 1.2.1 Thin Client Wrapping Google Maps REST APIs

- Each Maps feature (Geocoding, Directions, Time Zone, etc.) lives in its own **service module**.  
- A central `Client` orchestrates request building, authentication, HTTP dispatch, and response parsing.  
- All public types (requests & responses) are exported to ensure you get full IDE autocomplete.

### 1.2.2 Public Entrypoint: `src/index.ts`

- **`createClient(config)`** is your gateway.  
- Under the hood, it instantiates a `Client` class (in `src/client.ts`) and attaches all service methods.

### 1.2.3 Project Layout

```
├── src/                # Source code
│   ├── index.ts        # Public API entrypoint
│   ├── client.ts       # Core HTTP client and dispatcher
│   └── services/       # One folder per Maps API (geocode, directions, etc.)
├── docs/               # Written guides and reference
├── .github/workflows/  # CI pipelines (lint, tests, release)
├── LICENSE             # Apache 2.0
└── CHANGELOG.md        # Version history
```

---

## 1.3 Core Domain Abstractions

The library revolves around a few simple patterns:

1. **Service per API Group**  
   - `services/geocode.ts` exports `geocode()`  
   - `services/directions.ts` exports `directions()`  
2. **Typed Requests & Responses**  
   - Every method accepts a `{ params: ..., headers?: ... }` object  
   - Responses carry typed `.data` matching the Maps API schema  
3. **HTTP Dispatcher**  
   - A thin wrapper over `fetch` (or your adapter of choice)  
   - Handles retries, timeouts, and error parsing centrally  

### 1.3.1 How It Fits Together

- You call `client.geocode({ params: { address } })`  
- The service module builds a URL and query parameters  
- The `Client` class attaches your API key or OAuth token  
- An HTTP request is sent, the JSON is parsed, and a typed response is returned  

---

## 1.4 Installation & Your First Call

Let’s get hands-on!

### 1.4.1 Install via npm or yarn

```bash
# npm
npm install @googlemaps/rest

# yarn
yarn add @googlemaps/rest
```

### 1.4.2 Import and Create a Client

```ts
// src/index.ts → exports createClient
import { createClient } from "@googlemaps/rest";

const client = createClient({
  key: process.env.GOOGLE_MAPS_API_KEY,   // Or use OAuth credentials
  // Optional: custom fetch, timeout, retry settings
});
```

### 1.4.3 Make Your First API Call

```ts
async function runGeocode() {
  const response = await client.geocode({
    params: { address: "1600 Amphitheatre Parkway, Mountain View, CA" }
  });
  
  if (response.data.status === "OK") {
    console.log("Coordinates:", response.data.results[0].geometry.location);
  } else {
    console.error("Geocoding error:", response.data.status);
  }
}

runGeocode().catch(console.error);
```

---

## 1.5 Mapping the Codebase at a Glance

1. **Module Dependency**  
   - `src/index.ts` → `src/client.ts` → `src/services/*` → core HTTP  
2. **Information Flow**  
   - Call → Request Builder → HTTP Dispatcher → JSON Parser → Typed Response  
3. **Hierarchy**  
   - Client instance at top → service methods → request/response types  
4. **Core Interactions**  
   - Your code ↔ `createClient` ↔ `client.service()` ↔ Google Maps REST  

---

## 1.6 Conclusion

You now have:

- A clear picture of what this library is for and how it’s structured  
- The ability to install it, import the public API, and issue your first request  
- An overview of the main abstractions you’ll build upon in later chapters  

In **Chapter 2**, we’ll dive deeper into advanced configuration options (retry logic, custom fetch adapters) and explore more service methods like Directions and Time Zone. Let’s keep going!

---

# Chapter 2: Client Configuration & Factory Wiring  

# Chapter 2: Client Configuration & Factory Wiring

## Introduction

In this chapter we’ll explore how user-supplied options (API key, timeouts, retries, proxy settings, etc.) flow from your code all the way into the HTTP requests dispatched by each Maps service. We’ll walk through:

1. The `ClientOptions` interface  
2. The `createClient()` factory in **src/client.ts**  
3. How the HTTP adapter and each per-service class are instantiated and wired together  

By the end, you’ll understand how a single configuration object yields a fully-fledged client with Geocoding, Directions, Timezone, and all other services ready to go.

---

## 1. Defining `ClientOptions`

At the heart of our configuration is a simple interface:

```ts
// src/types.ts
export interface ClientOptions {
  apiKey: string               // Your Google Maps API key
  timeout?: number             // Milliseconds before aborting a request
  retries?: number             // Number of automatic retry attempts
  proxy?: string               // Optional proxy URL (e.g. "http://localhost:8080")
}
```

- **apiKey** is mandatory.  
- **timeout**, **retries**, and **proxy** are optional—sensible defaults will be applied if you omit them.  

These options travel as a single object through the factory into every layer of the client.

---

## 2. The `createClient()` Factory

The factory function in **src/client.ts** is responsible for:

1. **Merging defaults** with user-supplied options  
2. **Instantiating** the HTTP adapter  
3. **Wiring up** each service class using that adapter  

Here’s a simplified version:

```ts
// src/client.ts
import { ClientOptions } from "./types"
import { HTTPAdapter }    from "./adapter/http"
import { Geocoding }      from "./services/geocoding"
import { Directions }     from "./services/directions"
// ... import other services

const DEFAULTS = {
  timeout: 5_000,
  retries: 2
}

export function createClient(opts: ClientOptions) {
  // 1. Merge user options with defaults
  const config = {
    ...DEFAULTS,
    ...opts
  }

  // 2. Create a shared HTTP adapter
  const adapter = new HTTPAdapter(config)

  // 3. Instantiate each service with the adapter
  return {
    geocoding: new Geocoding(adapter),
    directions: new Directions(adapter),
    // ... other services
  }
}

export type Client = ReturnType<typeof createClient>
```

### Key Points

- We shallow-merge defaults **first**, then overwrite with any user values.  
- A **single** `HTTPAdapter` instance is shared across all services—this ensures consistent behavior (timeouts, retries, headers).  
- The returned object implements the `Client` API, exposing each service as a property.

---

## 3. Instantiation of Adapter & Services

### HTTPAdapter

The adapter abstracts the low-level HTTP logic:

```ts
// src/adapter/http.ts
import fetch from "node-fetch"
import { ClientOptions } from "../types"

export class HTTPAdapter {
  constructor(private opts: ClientOptions) {}

  async request<T>(path: string, params: Record<string, any>): Promise<T> {
    const url = new URL(`https://maps.googleapis.com/maps/api/${path}`)
    url.searchParams.set("key", this.opts.apiKey)
    Object.entries(params).forEach(([k,v]) => url.searchParams.set(k, String(v)))

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), this.opts.timeout)

    try {
      const res = await fetch(url.toString(), {
        signal: controller.signal,
        // Optionally route through a proxy:
        ...(this.opts.proxy && { agent: new HttpsProxyAgent(this.opts.proxy) })
      })
      clearTimeout(timer)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return (await res.json()) as T
    } finally {
      clearTimeout(timer)
    }
  }
}
```

### Per-Service Classes

Each service is a thin wrapper around `adapter.request()`. For example, the Geocoding service:

```ts
// src/services/geocoding.ts
import { HTTPAdapter } from "../adapter/http"

export class Geocoding {
  constructor(private adapter: HTTPAdapter) {}

  async geocode(address: string) {
    return this.adapter.request<GeocodeResponse>("geocode/json", { address })
  }

  async reverse(lat: number, lng: number) {
    return this.adapter.request<ReverseGeocodeResponse>(
      "geocode/json",
      { latlng: `${lat},${lng}` }
    )
  }
}
```

Other services (Directions, Timezone, Places, etc.) follow the same pattern:

1. Accept method-specific parameters  
2. Delegate to `adapter.request()` with the correct path and query parameters  

---

## 4. Putting It All Together

Here’s how you’d use the client in your application:

```ts
import { createClient } from "@your-org/maps-client"

const client = createClient({
  apiKey: "YOUR_KEY_HERE",
  timeout: 10_000,     // override default 5s
  retries: 3,
  proxy: "http://proxy:3128"
})

async function run() {
  const geo = await client.geocoding.geocode("1600 Amphitheatre Parkway")
  console.log("Coordinates:", geo.results[0].geometry.location)

  const route = await client.directions.route({
    origin: "San Francisco, CA",
    destination: "Los Angeles, CA"
  })
  console.log("Driving time:", route.routes[0].legs[0].duration.text)
}

run()
```

- All services share the same `timeout`, `retries`, and `proxy`.  
- You never have to pass your API key or network options to each call.  

---

## Conclusion

In this chapter, we’ve seen how a single `ClientOptions` object—containing your API key, timeouts, retry policy, and proxy settings—flows into:

1. A shared **HTTPAdapter** that handles request logic  
2. Individual **service classes** (Geocoding, Directions, etc.) that wrap concrete API endpoints  
3. The `createClient()` factory which merges defaults, creates the adapter, and wires up services  

With this wiring in place, you get a cohesive, easy-to-use client. Next up, we’ll dive into how to build requests, handle errors gracefully, and parse response data in Chapter 3: **Request Handling & Response Parsing**.

---

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

---

# Chapter 4: Parameter Utilities & Serialization  

# Chapter 4: Parameter Utilities & Serialization

## 4.1 Introduction

In this chapter, we’ll dive into two pure‐function modules—**`src/util.ts`** and **`src/serialize.ts`**—that power the parameter handling throughout our client library. These utilities take your typed parameters (with `undefined`/`null` values, camelCase keys, arrays, dates, LatLng objects, etc.), cleanse and convert them, and finally produce a URL‐encoded query string suitable for any HTTP request. By the end of this chapter you’ll understand:

- How we **drop** `undefined`/`null` values  
- How we convert **camelCase → snake_case**  
- How we format **arrays**, **dates**, and **LatLng** coordinates  
- How we **serialize** everything into a proper `?key1=val1&key2=val2…` string  

---

## 4.2 `src/util.ts`

This module contains small, reusable pure functions that manipulate individual values or object shapes. Let’s explore the key ones.

### 4.2.1 dropNilProps

We often don’t want `undefined` or `null` properties in our final query.  
`dropNilProps` removes those props from a flat object:

```ts
// src/util.ts
export function dropNilProps<T extends Record<string, any>>(obj: T): Partial<T> {
  return Object.entries(obj).reduce((acc, [key, val]) => {
    if (val !== undefined && val !== null) {
      acc[key] = val;
    }
    return acc;
  }, {} as Partial<T>);
}

// Usage
const raw = { address: "Paris", limit: undefined, region: null };
const clean = dropNilProps(raw);
// clean === { address: "Paris" }
```

### 4.2.2 camelToSnake

Google’s HTTP APIs expect `snake_case` query parameters. This helper converts a single string:

```ts
export function camelToSnake(str: string): string {
  return str
    .replace(/([A-Z])/g, "_$1")
    .toLowerCase();
}

// Usage
camelToSnake("locationBias"); // "location_bias"
```

### 4.2.3 Formatting Helpers

We need to serialize special types:

```ts
// src/util.ts

/** Format a JS Date to an ISO string (without milliseconds) */
export function formatDate(d: Date): string {
  return d.toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** Format LatLng-like { lat, lng } to "lat,lng" */
export function formatLatLng(latLng: { lat: number; lng: number }): string {
  return `${latLng.lat},${latLng.lng}`;
}
```

### 4.2.4 flattenArray

Sometimes APIs accept repeated keys or comma‐separated lists. We choose comma‐separated values by default:

```ts
export function arrayToCsv(arr: any[]): string {
  return arr.map(String).join(",");
}
```

---

## 4.3 `src/serialize.ts`

Once we have clean values and snake_case keys, we need to build the final query string.

### 4.3.1 encodeParam

A small wrapper around `encodeURIComponent`:

```ts
function encodeParam(value: string | number): string {
  return encodeURIComponent(String(value));
}
```

### 4.3.2 serializeParams

The core function. It:

1. Drops nil props  
2. Converts keys to `snake_case`  
3. Detects arrays, Dates, LatLng  
4. Encodes everything and joins with `&`  

```ts
// src/serialize.ts

import {
  dropNilProps,
  camelToSnake,
  formatDate,
  formatLatLng,
  arrayToCsv,
} from "./util";

type Primitive = string | number | boolean;
type ParamValue = Primitive | Date | { lat: number; lng: number } | Array<Primitive>;

export function serializeParams(params: Record<string, ParamValue | null | undefined>): string {
  const cleaned = dropNilProps(params);

  const parts: string[] = [];

  for (const [camelKey, rawValue] of Object.entries(cleaned)) {
    const key = camelToSnake(camelKey);

    let valueStr: string;

    if (rawValue instanceof Date) {
      valueStr = formatDate(rawValue);
    } else if (Array.isArray(rawValue)) {
      valueStr = arrayToCsv(rawValue);
    } else if (typeof rawValue === "object" && "lat" in rawValue && "lng" in rawValue) {
      valueStr = formatLatLng(rawValue as { lat: number; lng: number });
    } else {
      valueStr = String(rawValue);
    }

    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(valueStr)}`);
  }

  return parts.length > 0 ? `?${parts.join("&")}` : "";
}

// Usage example:
import { serializeParams } from "./serialize";

const query = serializeParams({
  address: "Tokyo, Japan",
  locationBias: { lat: 35.68, lng: 139.76 },
  arrivalTime: new Date("2024-01-01T09:00:00Z"),
  modes: ["driving", "toll"],
  limit: undefined,      // dropped
  region: null,          // dropped
});

// query === "?address=Tokyo%2C%20Japan&location_bias=35.68%2C139.76&arrival_time=2024-01-01T09:00:00Z&modes=driving%2Ctoll"
```

---

## 4.4 Putting It All Together

When a service method (e.g., `directions()`) receives user input:

1. You pass the raw parameter object to `serializeParams`  
2. You get back a query string  
3. Append it to the base URL and dispatch the HTTP request  

```ts
// src/client.ts (simplified)
import { serializeParams } from "./serialize";

async function getDirections(params: DirectionsRequest) {
  const qs = serializeParams(params);
  const url = `https://maps.googleapis.com/maps/api/directions/json${qs}`;
  const resp = await fetch(url);
  return resp.json();
}
```

This clear separation keeps your service logic focused on **what** you want, while `util.ts` + `serialize.ts` cleanly handle **how** to turn it into a valid HTTP call.

---

## 4.5 Conclusion

In this chapter we uncovered the mechanics behind:

- Pruning out `undefined`/`null` parameters  
- Converting camelCase keys to Google’s snake_case style  
- Formatting special types (arrays, dates, LatLng)  
- Building a URL‐encoded query string  

By centralizing these pure‐function utilities, our codebase remains DRY, predictable, and easy to test. In the next chapter, we’ll see how these query strings feed into our service classes and how we manage responses and errors. Keep going!

---

# Chapter 5: Service Modules & Domain Models  

# Chapter 5: Service Modules & Domain Models

## Introduction

In this chapter we’ll explore how each Google Maps API group (Geocoding, Directions, Places, etc.) is encapsulated in its own service module, and how requests and responses are strongly typed with domain models. We’ll see how these pieces wire together via the HTTP adapter using TypeScript generics for full compile‐time safety.

## 5.1 Folder & File Structure

A typical folder structure looks like this:

```
src/
├── index.ts              # Entry point & createClient()
├── client.ts             # MapsClient + Adapter
├── adapter/              # HTTP adapter implementation
│   └── adapter.ts
├── services/             # One service per API group
│   ├── geocoding.ts
│   ├── directions.ts
│   └── places.ts
└── models/               # Request & response interfaces
    ├── geocoding.ts
    ├── directions.ts
    └── places.ts
```

## 5.2 Defining Domain Models

Inside `src/models/`, we define the shape of request parameters and expected responses for each API.

### Example: `src/models/geocoding.ts`

```ts
// Request parameters for Geocoding API
export interface GeocodingRequest {
  address?: string;
  components?: Record<string, string>;
  latlng?: { lat: number; lng: number };
  place_id?: string;
  language?: string;
  region?: string;
}

// Sub‐structure for a single geocode result
export interface AddressComponent {
  long_name: string;
  short_name: string;
  types: string[];
}

// Full response from Geocoding API
export interface GeocodingResponse {
  results: Array<{
    formatted_address: string;
    geometry: {
      location: { lat: number; lng: number };
      location_type: string;
      viewport: {
        northeast: { lat: number; lng: number };
        southwest: { lat: number; lng: number };
      };
    };
    address_components: AddressComponent[];
    place_id: string;
    types: string[];
  }>;
  status: 'OK' | 'ZERO_RESULTS' | string;
  error_message?: string;
}
```

> Note: We keep request and response interfaces in separate files for clarity and easier maintenance.

## 5.3 Service Modules

Each service module encapsulates one Maps API endpoint group. It exposes methods that accept a typed request and return a typed response, internally delegating to the adapter.

### Example: `src/services/geocoding.ts`

```ts
import {
  GeocodingRequest,
  GeocodingResponse,
} from '../models/geocoding';
import { AdapterRequestConfig, HttpAdapter } from '../adapter/adapter';

export class GeocodingService {
  constructor(private adapter: HttpAdapter) {}

  /**
   * Performs a geocode lookup.
   */
  async geocode(
    params: GeocodingRequest
  ): Promise<GeocodingResponse> {
    const config: AdapterRequestConfig = {
      method: 'GET',
      url: '/geocode/json',
      params,
    };

    // adapter.request<T> ensures correct typing for the response
    return this.adapter.request<GeocodingResponse>(config);
  }

  /**
   * Reverse geocode from lat/lng to address.
   */
  async reverseGeocode(
    params: GeocodingRequest
  ): Promise<GeocodingResponse> {
    const config: AdapterRequestConfig = {
      method: 'GET',
      url: '/geocode/json',
      params,
    };
    return this.adapter.request<GeocodingResponse>(config);
  }
}
```

#### Key Points

- **One service per file**: `GeocodingService` lives in its own file alongside other services like `DirectionsService` and `PlacesService`.
- **Strongly typed**: Input `params` and return values are fully typed.
- **Adapter generics**: `adapter.request<GeocodingResponse>` binds the HTTP call to the expected response shape.

## 5.4 Wiring Services into the Client

In `src/client.ts`, we instantiate each service, passing a shared HTTP adapter instance:

```ts
import { GeocodingService } from './services/geocoding';
import { DirectionsService }   from './services/directions';
import { PlacesService }       from './services/places';
import { HttpAdapter, AdapterConfig } from './adapter/adapter';

export class MapsClient {
  public geocoding: GeocodingService;
  public directions: DirectionsService;
  public places: PlacesService;

  private adapter: HttpAdapter;

  constructor(config: AdapterConfig) {
    this.adapter = new HttpAdapter(config);
    this.geocoding = new GeocodingService(this.adapter);
    this.directions = new DirectionsService(this.adapter);
    this.places = new PlacesService(this.adapter);
  }
}
```

And in `src/index.ts`:

```ts
import { MapsClient } from './client';
import type { AdapterConfig } from './adapter/adapter';

/**
 * Factory to create a MapsClient.
 */
export function createClient(config: AdapterConfig): MapsClient {
  return new MapsClient(config);
}

// Re‐export types if needed
export * from './models/geocoding';
export * from './models/directions';
export * from './models/places';
```

## 5.5 Using the Client

```ts
import { createClient } from '@your-org/maps-client';

const client = createClient({ apiKey: 'YOUR_API_KEY' });

async function run() {
  const response = await client.geocoding.geocode({
    address: '1600 Amphitheatre Parkway, Mountain View, CA',
  });
  console.log(response.results[0].formatted_address);
}

run();
```

## Conclusion

In this chapter we covered:

- **Service modules**: One file per API group, encapsulating request logic.
- **Domain models**: Strongly typed request and response interfaces.
- **Adapter wiring**: Using `adapter.request<T>` to bind HTTP calls to typed responses.
- **Client setup**: How services are instantiated under a single `MapsClient`.

This pattern keeps our codebase organized, type‐safe, and easy to extend as new Maps APIs are added. In the next chapter, we’ll dive into error handling and retry strategies for resilient API calls.

---

# Chapter 6: Making API Calls: End-to-End Flow  

# Chapter 6: Making API Calls: End-to-End Flow

## Introduction

In this chapter, we’ll trace a full HTTP call from your application code all the way through to a typed response object. Using the Time Zone API as our running example, we’ll cover:

- How `createClient()` wires up your API client  
- What happens when you call `client.timezone.get()`  
- Parameter normalization & serialization  
- The HTTP adapter layer (Axios)  
- Response deserialization and type safety  
- Error propagation  

By the end, you’ll understand exactly how requests move through our TypeScript-first Google Maps client library.

---

## 6.1 Call Flow Overview

High-level information flow for a `/timezone` call:

1. **createClient** → returns a configured client  
2. **client.timezone.get()** → service method invocation  
3. **normalize** → ensure parameters are valid and defaults applied  
4. **serialize** → build URL, query string, headers, body  
5. **adapter** → dispatch HTTP request via Axios  
6. **adapter** → receive raw response  
7. **deserialize** → map raw JSON to a typed response  
8. **return** → application code receives a `Promise<TimezoneResponse>`  

```
createClient
    ↓
timezone.get(params)
    ↓
util.normalize(params)
    ↓
util.serialize(path, params)
    ↓
axiosAdapter(request)
    ↓
raw HTTP response
    ↓
util.deserialize<TimezoneResponse>(response)
    ↓
typed TimezoneResponse
```

---

## 6.2 Stepping Through the Code

### 6.2.1 Client Creation (`createClient`)

Your journey starts in `src/index.ts`:

```ts
import { createClient } from "@googlemaps/maps";

const client = createClient({
  key: "YOUR_API_KEY",
  // optional: fetch implementation, region, timeout, etc.
});
```

- **createClient** sets up default headers, your API key, the HTTP adapter, and wires each service under `client`.

### 6.2.2 Service Method Invocation (`timezone.get`)

Each Maps API group (Geocoding, Directions, Timezone…) is exposed as a property:

```ts
// src/services/timezone.ts
export function get(
  params: TimezoneRequest
): Promise<TimezoneResponse> {
  return fetch("/timezone", params);
}

// user code
const resultPromise = client.timezone.get({
  location: { lat: 40.6892, lng: -74.0445 },
  timestamp: Math.floor(Date.now() / 1000),
});
```

- `fetch` is a thin wrapper that kicks off normalization, serialization, the HTTP call, then deserialization.

### 6.2.3 Parameter Normalization & Validation

Before building a request, we normalize:

```ts
// src/util/params.ts
export function normalize<T>(params: T): T {
  // e.g. convert Date → UNIX timestamp,
  // ensure required keys are present,
  // apply defaults (language, region).
  return params;
}
```

### 6.2.4 Request Serialization

Next, we serialize the endpoint, query string, and body:

```ts
// src/util/serialize.ts
export function serialize(
  path: string,
  params: Record<string, any>
): HttpRequest {
  const url = `${BASE_URL}${path}`;
  const query = new URLSearchParams(params as any).toString();
  return {
    method: "GET",
    url: `${url}?${query}`,
    headers: { "Content-Type": "application/json" },
  };
}
```

### 6.2.5 Dispatching with the Axios Adapter

The adapter layer decouples HTTP from your logic:

```ts
// src/adapter/axios.ts
import axios, { AxiosRequestConfig } from "axios";

export async function axiosAdapter(
  req: HttpRequest
): Promise<HttpResponse> {
  const config: AxiosRequestConfig = {
    url: req.url,
    method: req.method,
    headers: req.headers,
    data: req.body,
    timeout: req.timeout,
  };
  const response = await axios(config);
  return {
    status: response.status,
    headers: response.headers,
    data: response.data,
  };
}
```

### 6.2.6 Response Deserialization & Typed Return

Finally, we turn raw JSON into a typed interface:

```ts
// src/util/deserialize.ts
export function deserialize<T>(
  httpRes: HttpResponse
): T {
  // optionally check httpRes.status, map error codes
  return httpRes.data as T;
}
```

And `fetch` ties it all together:

```ts
// src/internal/fetch.ts
export async function fetch<P, R>(
  path: string,
  params: P
): Promise<R> {
  const normalized = normalize(params);
  const request = serialize(path, normalized);
  const raw = await axiosAdapter(request);
  return deserialize<R>(raw);
}
```

---

## 6.3 Example: Fetching a Time Zone

Putting it all into one snippet:

```ts
import { createClient } from "@googlemaps/maps";

async function getTimeZone() {
  const client = createClient({ key: "YOUR_KEY" });
  
  try {
    const response = await client.timezone.get({
      location: { lat: 40.6892, lng: -74.0445 },
      timestamp: Math.floor(Date.now() / 1000),
    });
    console.log("Time zone ID:", response.timeZoneId);
    console.log("Offset (seconds):", response.dstOffset + response.rawOffset);
  } catch (err) {
    console.error("Failed to fetch timezone:", err);
  }
}

getTimeZone();
```

- **Async/Await** makes the flow linear and readable.  
- You receive a fully typed `TimezoneResponse` with `timeZoneId`, `dstOffset`, `rawOffset`, etc.

---

## 6.4 Promise-Based Usage

If you prefer `.then()/.catch()`:

```ts
client
  .timezone.get({ /* … */ })
  .then((res) => {
    console.log(res.timeZoneId);
  })
  .catch((err) => {
    console.error(err);
  });
```

---

## 6.5 Error Propagation

- Network errors or 4xx/5xx responses throw inside `axiosAdapter`.  
- `fetch` doesn’t swallow errors—any throw bubbles up to your call site.  
- You can extend `deserialize` to inspect `status` and throw custom typed errors (e.g. `ApiError`).

---

## Conclusion

In this chapter, you’ve seen how a simple `client.timezone.get()` call:

1. Normalizes and validates your parameters  
2. Serializes them into an HTTP request  
3. Uses Axios under the hood to dispatch the call  
4. Deserializes the JSON response into a fully typed result  
5. Propagates errors so you can handle them in your application  

This end-to-end view should empower you to:

- Debug requests by inserting logs in `normalize`, `serialize`, or the adapter  
- Extend the client with custom adapters (e.g. `fetch` or `got`)  
- Add request/response middleware for retries, caching, or instrumentation  

In the next chapter, we’ll explore advanced patterns like middleware and pagination helpers. Stay tuned!

---

# Chapter 7: Testing, Documentation & Release Workflow  

# Chapter 7: Testing, Documentation & Release Workflow

## Introduction

In this chapter we’ll cover the vital “plumbing” that surrounds our TypeScript-first Google Maps client library: writing tests with Jest, generating API docs with TypeDoc, and automating releases via GitHub Actions (release-please). We’ll also touch on project governance—licenses and contribution guidelines—so you can confidently develop, document, and ship new features.

---

## 7.1 Testing with Jest

### 7.1.1 Installing & Configuring Jest

First, add Jest and friends:

```bash
npm install --save-dev jest ts-jest @types/jest
```

Create a `jest.config.js` at the repo root:

```js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/**/*.test.ts'],
  moduleFileExtensions: ['ts', 'js', 'json'],
  collectCoverage: true,
  coverageDirectory: '<rootDir>/coverage',
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 85,
      statements: 85,
    },
  },
};
```

### 7.1.2 Unit vs. Integration Tests

- **Unit tests**: isolate a single class or function, mocking external HTTP calls.
- **Integration tests**: exercise actual HTTP requests against a test key or stub server.

Example unit test for `GeocodingService`:

```ts
// src/services/geocoding.test.ts
import { GeocodingService } from './geocoding';
import nock from 'nock';

describe('GeocodingService (unit)', () => {
  const service = new GeocodingService({ apiKey: 'TEST_KEY' });

  beforeAll(() => {
    nock('https://maps.googleapis.com')
      .get('/maps/api/geocode/json')
      .query(true)
      .reply(200, { results: [{ formatted_address: '123 Test St' }], status: 'OK' });
  });

  it('should return formatted address', async () => {
    const resp = await service.geocode({ address: 'Test St' });
    expect(resp.results[0].formatted_address).toBe('123 Test St');
  });
});
```

For integration tests, skip `nock`, point at a sandbox environment, and guard with an `API_KEY` env var.

```ts
// src/integration/geocoding.integration.test.ts
import { GeocodingService } from '../services/geocoding';

describe('GeocodingService (integration)', () => {
  const key = process.env.GEOCODING_KEY;
  if (!key) {
    console.warn('Skipping integration tests; GEOCODING_KEY not set.');
    return;
  }
  const service = new GeocodingService({ apiKey: key });

  it('resolves a real address', async () => {
    const res = await service.geocode({ address: 'New York, NY' });
    expect(res.results.length).toBeGreaterThan(0);
  });
});
```

Run tests with:

```bash
npm test
```

---

## 7.2 Generating Documentation with TypeDoc

### 7.2.1 Installing & Configuring TypeDoc

```bash
npm install --save-dev typedoc typedoc-plugin-markdown
```

Add a `typedoc.json`:

```json
{
  "entryPoints": ["src/index.ts"],
  "out": "docs/api",
  "plugin": ["typedoc-plugin-markdown"],
  "excludePrivate": true,
  "excludeInternal": true,
  "includeVersion": true
}
```

### 7.2.2 Generating Docs

Add to `package.json`:

```json
{
  "scripts": {
    "docs": "typedoc"
  }
}
```

Then:

```bash
npm run docs
```

This produces markdown files under `docs/api/`. Hook these into your static site generator (GitHub Pages, Docusaurus, etc.).

---

## 7.3 Automating Releases with GitHub Actions

We follow **Conventional Commits**, generate a changelog, and publish to npm automatically.

### 7.3.1 Conventional Commits & Changelog

Commit messages look like:

```
feat(geocoding): add region bias option
fix(client): handle network timeouts
```

We use `release-please` to parse these and bump versions.

### 7.3.2 GitHub Workflow (`.github/workflows/release.yml`)

```yaml
name: Release

on:
  push:
    branches:
      - main

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/release-please-action@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          release-type: node
          package-name: "@your-org/maps-client"
          changelog-types: feat, fix, perf, docs
```

This action will:
1. Analyze commits since last tag.
2. Generate or update `CHANGELOG.md`.
3. Bump `package.json` version.
4. Create a new GitHub Release.

### 7.3.3 Automatic npm Publishing

Add a second job that runs on the release tag:

```yaml
  publish:
    needs: release
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

Store your `NPM_TOKEN` in GitHub Secrets. After the release PR is merged, the `publish` job will push the package to npm.

---

## 7.4 Governance

### 7.4.1 License: Apache 2.0

Our project is Apache-2.0 licensed. The `LICENSE` file at root spells out permissions and limitations.

### 7.4.2 CONTRIBUTING.md

Defines:
- Code style (Prettier, ESLint).
- Branching strategy (`main` for release-ready code, `feat/*` and `fix/*` branches).
- Pull request checklist (tests, docs, changelog entry).

### 7.4.3 CODE_OF_CONDUCT.md

We adopt a standard Contributor Covenant. It ensures a respectful, inclusive community. Link to it in PR templates and README.

---

## Conclusion

By integrating Jest for thorough unit and integration tests, TypeDoc for clear API documentation, and GitHub Actions with release-please for automated versioning and npm publishing, we establish a robust, repeatable workflow. Coupled with clear governance docs (LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md), your thin wrapper around Google Maps services becomes a well-maintained, community-friendly open-source project. Happy coding and releasing!

---

