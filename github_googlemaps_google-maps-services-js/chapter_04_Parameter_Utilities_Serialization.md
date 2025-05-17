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