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