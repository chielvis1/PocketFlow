# Chapter 3: **Working with Google Maps in React: Loading and Displaying the Map**  

# Chapter 3: Working with Google Maps in React: Loading and Displaying the Map

In this chapter, we will dive into integrating Google Maps into a React application using the `@react-google-maps/api` library. This library provides React-friendly abstractions over the Google Maps JavaScript API, making it easier to load the map script asynchronously and render interactive maps with markers.

We will cover:

- How to load the Google Maps JavaScript API asynchronously using the `useLoadScript` hook.
- Rendering a map centered on a default location using the `<GoogleMap>` component.
- Adding a marker to the map using the `<MarkerF>` component.

By the end of this chapter, you will understand the core concepts behind integrating Google Maps into a React app and be able to render a map with a marker in your project.

---

## 3.1 Introduction to `@react-google-maps/api`

Google Maps API is powerful but can be cumbersome to integrate directly into React apps due to its imperative and script-based nature. The `@react-google-maps/api` library abstracts away the manual script loading and provides declarative React components and hooks to work with maps.

Key components and hooks we'll use:

- **`useLoadScript`**: A React hook that asynchronously loads the Google Maps JavaScript API script. It manages the loading state and errors.
- **`<GoogleMap>`**: A React component that renders the map inside your component tree. It accepts props like `center`, `zoom`, and event handlers.
- **`<MarkerF>`**: A React component representing a marker on the map. The `F` suffix indicates a functional component version optimized for React.

This library helps us keep our React app declarative and clean while leveraging the full power of Google Maps.

---

## 3.2 Setting Up the Google Maps API Key

Before loading the map, you need a Google Maps API key with Maps JavaScript API enabled:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable the **Maps JavaScript API**.
4. Create an API key.
5. Restrict the key to your app's domain (recommended).
6. Store this key securely (e.g., environment variables).

In a Next.js app, you typically store it in a `.env.local` file:

```env
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_api_key_here
```

The `NEXT_PUBLIC_` prefix exposes the variable to the browser.

---

## 3.3 Loading the Google Maps Script Asynchronously with `useLoadScript`

The Google Maps API is loaded via a script tag, which is asynchronous and external. `useLoadScript` handles this for us:

- It injects the script tag.
- Tracks loading status and errors.
- Prevents loading the script multiple times.

Here is an example of how to use it:

```tsx
import React from 'react';
import { useLoadScript } from '@react-google-maps/api';

const libraries = ['places']; // Optional libraries you might need

function MapLoader() {
  const { isLoaded, loadError } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
    libraries,
  });

  if (loadError) return <div>Error loading maps</div>;
  if (!isLoaded) return <div>Loading Maps...</div>;

  return <Map />;
}
```

**Explanation:**

- `isLoaded`: Boolean indicating whether the script has finished loading.
- `loadError`: Any error encountered during script loading.
- Once loaded, you can render the map component safely.

---

## 3.4 Rendering the Map with `<GoogleMap>`

After the script loads, you can render the map using the `<GoogleMap>` component.

Example:

```tsx
import React from 'react';
import { GoogleMap, MarkerF } from '@react-google-maps/api';

const containerStyle = {
  width: '100%',
  height: '400px',
};

// Default center coordinates (e.g., New York City)
const center = {
  lat: 40.7128,
  lng: -74.0060,
};

function Map() {
  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={center}
      zoom={12}
    >
      <MarkerF position={center} />
    </GoogleMap>
  );
}
```

**Key props:**

- `mapContainerStyle`: CSS styles for the map container. Width and height must be set explicitly.
- `center`: Latitude and longitude to center the map.
- `zoom`: Zoom level (1–20, where higher numbers zoom in closer).

---

## 3.5 Adding a Marker with `<MarkerF>`

Markers indicate specific locations on the map.

- `<MarkerF>` accepts a `position` prop with latitude and longitude.
- It can accept event handlers like `onClick` for interactivity.

Example:

```tsx
<MarkerF
  position={{ lat: 40.7128, lng: -74.0060 }}
  onClick={() => alert('Marker clicked!')}
/>
```

In our simple example, we add one marker centered on the map.

---

## 3.6 Full Example: Loading and Displaying a Map with a Marker

Putting it all together:

```tsx
import React from 'react';
import { useLoadScript, GoogleMap, MarkerF } from '@react-google-maps/api';

const containerStyle = {
  width: '100%',
  height: '400px',
};

const center = {
  lat: 40.7128,
  lng: -74.0060,
};

const libraries = ['places'];

export default function MapLoader() {
  const { isLoaded, loadError } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
    libraries,
  });

  if (loadError) return <div>Error loading maps</div>;
  if (!isLoaded) return <div>Loading Maps...</div>;

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={center}
      zoom={12}
    >
      <MarkerF position={center} />
    </GoogleMap>
  );
}
```

This component:

- Loads the Google Maps script asynchronously.
- Displays loading or error states.
- Renders the map centered on NYC.
- Places a marker at the center.

---

## 3.7 Summary

In this chapter, you learned how to:

- Use the `@react-google-maps/api` library to load the Google Maps JavaScript API asynchronously with `useLoadScript`.
- Render a Google Map centered on a default location using the `<GoogleMap>` component.
- Add a marker to the map with the `<MarkerF>` component.

These abstractions allow you to work with Google Maps in React declaratively and efficiently, handling script loading and map rendering seamlessly.

In the next chapter, we will explore how to customize the map further and handle user interactions such as clicking and dragging markers.