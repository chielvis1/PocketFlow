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