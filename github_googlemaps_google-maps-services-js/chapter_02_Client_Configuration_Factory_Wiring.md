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