# Chapter 3: **Displaying the Google Map**

Okay, here is Chapter 3: Displaying the Google Map, written according to your requirements and based on the provided context.

```markdown
# Chapter 3: Displaying the Google Map

Welcome back! In this chapter, we'll take the essential setup from Chapter 2 (loading the API script) and finally display the core visual component of our application: the Google Map itself. This is where we integrate the `GoogleMap` component from the `@react-google-maps/api` library and configure its basic appearance and initial view.

## The `GoogleMap` Component

The `@react-google-maps/api` library provides the `GoogleMap` component, which is a React wrapper around the native Google Maps JavaScript API's `Map` object. This component is the primary element you'll use to render the interactive map on your page.

To use it, you simply render the `<GoogleMap>` component in your JSX after ensuring the API script has loaded.

## Essential Map Configuration

The `GoogleMap` component requires several props to determine its appearance and initial state:

1.  **`mapContainerStyle`**: This is a required prop that defines the size and styling of the `div` element that will contain the map. You need to provide CSS styles to give the map a specific width and height, otherwise, it won't be visible.
2.  **`center`**: This prop takes an object with `lat` (latitude) and `lng` (longitude) properties, specifying the geographical coordinates where the map should be initially centered.
3.  **`zoom`**: A number representing the initial zoom level of the map. Higher numbers mean more zoomed in.

Additionally, we'll often want to interact with the underlying Google Maps `Map` instance directly (for example, to add markers, control the view programmatically, etc.). The `@react-google-maps/api` library provides lifecycle callbacks for this:

*   **`onLoad`**: A function that is called when the map component has finished loading and is ready. It receives the native Google Maps `Map` instance as an argument. We'll use this to store the map instance in our component's state.
*   **`onUnmount`**: A function called when the map component is unmounted (removed from the DOM). This is a good place to clean up references to the map instance to prevent memory leaks.

## Integrating the Map in `app/page.tsx`

Let's look at how these pieces come together in our `app/page.tsx` file. We'll build upon the script loading logic we discussed in Chapter 2.

```typescript
'use client';

import { useState, useMemo, useCallback } from 'react';
import { GoogleMap, useLoadScript, MarkerF } from '@react-google-maps/api';
import PlacesAutocomplete from './components/PlacesAutocomplete'; // We'll use this later

// Define the libraries we need (geocoding is useful)
const libraries: (keyof google.maps.drawing.OverlayType | keyof google.maps.services.Service | keyof google.maps.visualization.MapsEngineLayer)[] = ['places'];

export default function Home() {
    // 1. Load the Google Maps script
    const { isLoaded } = useLoadScript({
        googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!, // Ensure your API key is set in .env.local
        libraries: libraries,
    });

    // 2. State to hold the map instance
    const [map, setMap] = useState<google.maps.Map | null>(null);

    // 3. State for map center and zoom (can be updated later)
    const [center, setCenter] = useState({ lat: 43.6532, lng: -79.3832 }); // Default center (e.g., Toronto)
    const [zoom, setZoom] = useState(10); // Default zoom level

    // Use useMemo for the center to prevent unnecessary re-renders of the map component
    // This is a common optimization pattern.
    const memoizedCenter = useMemo(() => center, [center]);

    // 4. Define map container style
    const mapContainerStyle = {
        width: '100%',
        height: 'calc(100vh - 60px)', // Example: full height minus a header/navbar height
    };

    // 5. Define onLoad and onUnmount handlers
    const onLoad = useCallback(function callback(map: google.maps.Map) {
        // Store the map instance in state
        setMap(map);
        // Optional: You can fit bounds here if you have them
        // const bounds = new window.google.maps.LatLngBounds(center);
        // map.fitBounds(bounds);
    }, []); // Dependencies: [] - this function doesn't depend on props/state that change frequently

    const onUnmount = useCallback(function callback(map: google.maps.Map) {
        // Clean up the map instance reference
        setMap(null);
    }, []); // Dependencies: []

    // 6. Render loading state or the map
    if (!isLoaded) return <div>Loading Map...</div>;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            {/* Places Autocomplete component will go here */}
            {/* <PlacesAutocomplete onSelectPlace={handlePlaceSelect} /> */}

            {/* The Google Map component */}
            <GoogleMap
                mapContainerStyle={mapContainerStyle}
                center={memoizedCenter}
                zoom={zoom}
                onLoad={onLoad}
                onUnmount={onUnmount}
                options={{
                     // Optional: Disable default UI elements for a cleaner look
                     // disableDefaultUI: true,
                     // zoomControl: true,
                }}
            >
                {/* Markers and other map overlays will be placed here */}
                {/* <MarkerF position={memoizedCenter} /> */}
            </GoogleMap>
        </div>
    );
}
```

## Code Explanation

Let's break down the key parts of the code snippet above:

1.  **`useLoadScript`**: As seen in Chapter 2, this hook handles asynchronously loading the Google Maps JavaScript API script. `isLoaded` will be `true` once the script is ready. We also specify the `places` library, which will be needed for the autocomplete functionality later.
2.  **`useState<google.maps.Map | null>(null)`**: We declare a state variable `map` to hold the Google Maps `Map` instance. It's initialized to `null`.
3.  **`useState({ lat: ..., lng: ... })` and `useState(10)`**: State variables `center` and `zoom` are initialized to define the map's starting view. We use state so these values can potentially be updated later (e.g., when a user searches for a location).
4.  **`useMemo(() => center, [center])`**: The `center` prop of `GoogleMap` should ideally be a stable object reference. While our `center` state *can* change, using `useMemo` ensures that the *object itself* is only recreated if the `center` state value changes. This is a minor but good optimization practice to prevent the `GoogleMap` component from unnecessarily re-rendering if only the reference identity changed but the lat/lng values were the same (though less likely with state updates).
5.  **`mapContainerStyle`**: A simple JavaScript object defining the necessary CSS for the map container. We've set it to take full width and most of the viewport height. Adjust this based on your layout needs.
6.  **`onLoad` and `onUnmount`**: These `useCallback` wrapped functions handle the map's lifecycle. `onLoad` receives the actual `map` object from the Google Maps API and stores it in our component's state using `setMap`. `onUnmount` is called when the map is removed, and we clean up by setting `map` back to `null`. Using `useCallback` is recommended for these props to ensure they have stable references, preventing unnecessary re-renders of the `GoogleMap` component.
7.  **Conditional Rendering (`if (!isLoaded)`)**: We check the `isLoaded` flag from `useLoadScript`. If the script hasn't finished loading, we display a simple "Loading Map..." message. Only when `isLoaded` is `true` do we render the `<GoogleMap>` component.
8.  **`<GoogleMap>` JSX**: This is where the component is actually rendered. We pass the `mapContainerStyle`, `center` (using the memoized value), `zoom`, `onLoad`, and `onUnmount` props. The `options` prop is commented out but shows where you could add more advanced configuration for the map's behavior and appearance.

## Running and Verifying

1.  Ensure you have set your `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` environment variable correctly in a `.env.local` file at the root of your project (as discussed in Chapter 2 implicitly).
2.  Save the changes to `app/page.tsx`.
3.  Make sure your Next.js development server is running (`npm run dev` or `yarn dev`).
4.  Open your browser and navigate to `http://localhost:3000` (or the address where your app is served).

You should now see a Google Map displayed on the page, centered around the coordinates you specified and at the given zoom level. If you only see a gray box or a loading message that doesn't go away, double-check your API key, environment variable setup, and browser console for errors.

## Conclusion

Congratulations! You've successfully integrated and displayed a basic Google Map using the `@react-google-maps/api` library within your Next.js application. You now have the foundation for building location-aware features. In the next chapters, we'll explore how to make this map more interactive and useful, starting with adding markers.
```