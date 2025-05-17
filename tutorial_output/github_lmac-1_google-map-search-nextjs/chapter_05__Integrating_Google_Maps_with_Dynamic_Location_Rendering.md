# Chapter 5: **Integrating Google Maps with Dynamic Location Rendering**  

# Chapter 5: Integrating Google Maps with Dynamic Location Rendering

## Introduction

In this chapter, we will explore how to integrate Google Maps into your Next.js application using the `@react-google-maps/api` package. We will focus on the `Home` component (`app/page.tsx`) as a **client component** responsible for managing the map's state, dynamically updating its center based on user input. You will learn how to embed the `GoogleMap` and `MarkerF` components, how to geocode addresses into latitude and longitude coordinates using `getGeocode` and `getLatLng` utilities, and how to reflect these changes dynamically on the map.

By the end of this chapter, you will understand the fundamentals behind declarative Google Maps rendering within a React environment, the significance of client components in Next.js 13+, and how to manage state effectively with hooks like `useState`.

---

## 5.1 Setting Up the `Home` Component as a Client Component

Next.js 13 introduced React Server Components by default. However, to manage interactive state or browser-only APIs (like Google Maps), we need to designate components as **client components**. This is done by adding `"use client";` at the top of the file.

```tsx
// app/page.tsx
"use client";

import React, { useState } from "react";
import { GoogleMap, MarkerF, useLoadScript } from "@react-google-maps/api";

// Additional imports will be covered later
```

### Why `"use client";`?

- Enables React hooks like `useState` and `useEffect` that require client-side rendering.
- Allows interaction with browser APIs (e.g., Google Maps JavaScript API).
- Essential for components needing dynamic updates and user interaction.

---

## 5.2 Managing Map State with `useState`

The core of dynamic location rendering lies in maintaining the map's center coordinates in state so that when a user searches or selects a new location, the map re-centers automatically.

We typically start with a default location, for example, New York City coordinates:

```tsx
const DEFAULT_CENTER = { lat: 40.7128, lng: -74.006 };
```

Inside the `Home` component, declare state for the map center:

```tsx
const [center, setCenter] = useState<{ lat: number; lng: number }>(DEFAULT_CENTER);
```

This `center` state will be passed to the `GoogleMap` component to control its viewport.

---

## 5.3 Embedding Google Map and Marker Components

The `@react-google-maps/api` package provides declarative React components to work with Google Maps. Two key components are:

- **`GoogleMap`**: The map container.
- **`MarkerF`**: A marker on the map (the `F` variant supports React 18's concurrent features).

### Loading the Google Maps Script

Before rendering the map, you must load the Google Maps API script using the `useLoadScript` hook:

```tsx
const { isLoaded, loadError } = useLoadScript({
  googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
  libraries: ["places"], // if you use Places Autocomplete or Geocoding services
});
```

### Rendering the Map and Marker

```tsx
if (loadError) return <div>Error loading maps</div>;
if (!isLoaded) return <div>Loading Maps...</div>;

return (
  <GoogleMap
    zoom={14}
    center={center}
    mapContainerStyle={{ width: "100%", height: "400px" }}
  >
    <MarkerF position={center} />
  </GoogleMap>
);
```

This renders a map centered at `center` with a marker positioned exactly there.

---

## 5.4 Geocoding Addresses to Coordinates

To dynamically update the map center based on user input (e.g., an address), we need to convert addresses into latitude and longitude. This process is called **geocoding**.

### Using `getGeocode` and `getLatLng`

The `@react-google-maps/api` package exports utility functions to help with geocoding:

- **`getGeocode({ address })`**: Takes a string address and returns geocode results.
- **`getLatLng(geocodeResult)`**: Extracts `{ lat, lng }` from a geocode result.

### Example: Geocode an Address and Update the Map

Here is an example function inside the `Home` component that takes an address string, geocodes it, and updates the map center state:

```tsx
import { getGeocode, getLatLng } from "use-places-autocomplete";

async function handleAddressSelect(address: string) {
  try {
    const results = await getGeocode({ address });
    if (results.length === 0) throw new Error("No results found");
    const { lat, lng } = await getLatLng(results[0]);
    setCenter({ lat, lng });
  } catch (error) {
    console.error("Error geocoding address:", error);
  }
}
```

You can call `handleAddressSelect` whenever the user selects or inputs a new address.

---

## 5.5 Putting It All Together: Complete `Home` Component Example

Below is a simplified but complete example of the `Home` component integrating all the pieces:

```tsx
"use client";

import React, { useState } from "react";
import { GoogleMap, MarkerF, useLoadScript } from "@react-google-maps/api";
import { getGeocode, getLatLng } from "use-places-autocomplete";

const DEFAULT_CENTER = { lat: 40.7128, lng: -74.006 };

export default function Home() {
  const [center, setCenter] = useState(DEFAULT_CENTER);
  const [address, setAddress] = useState("");

  const { isLoaded, loadError } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
    libraries: ["places"],
  });

  async function handleSearch() {
    if (!address) return;
    try {
      const results = await getGeocode({ address });
      if (results.length === 0) throw new Error("No results found");
      const { lat, lng } = await getLatLng(results[0]);
      setCenter({ lat, lng });
    } catch (error) {
      console.error("Failed to geocode address:", error);
    }
  }

  if (loadError) return <div>Error loading maps</div>;
  if (!isLoaded) return <div>Loading Maps...</div>;

  return (
    <div>
      <input
        type="text"
        placeholder="Enter address"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        style={{ width: "300px", padding: "8px" }}
      />
      <button onClick={handleSearch} style={{ marginLeft: "10px" }}>
        Search
      </button>

      <GoogleMap
        zoom={14}
        center={center}
        mapContainerStyle={{ width: "100%", height: "400px", marginTop: "20px" }}
      >
        <MarkerF position={center} />
      </GoogleMap>
    </div>
  );
}
```

### Explanation

- The component initializes with a default center.
- An input field allows users to enter an address.
- Upon clicking **Search**, `handleSearch` geocodes the address and updates the map center.
- The map and marker re-render automatically based on the updated `center` state.

---

## 5.6 Summary and Best Practices

- **Client Components:** Always declare `"use client";` when using hooks or browser APIs.
- **State Management:** Use `useState` to track dynamic values like map center coordinates.
- **Declarative Map Rendering:** Use `GoogleMap` and `MarkerF` components from `@react-google-maps/api` to declaratively render maps and markers.
- **Geocoding Utilities:** Leverage `getGeocode` and `getLatLng` for converting addresses to lat/lng coordinates.
- **Error Handling:** Always handle errors gracefully, especially for user inputs and external API calls.

---

## Conclusion

Integrating Google Maps with dynamic location rendering enhances the user experience by providing interactive, real-time map updates. By managing the map state within a client component and utilizing declarative APIs, you can create responsive and intuitive map features in your Next.js application.

In the next chapter, we will build upon this foundation by integrating places autocomplete functionality to improve address input and selection, creating a seamless location search experience.

---

# End of Chapter 5