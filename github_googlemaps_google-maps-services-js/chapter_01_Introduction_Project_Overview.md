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