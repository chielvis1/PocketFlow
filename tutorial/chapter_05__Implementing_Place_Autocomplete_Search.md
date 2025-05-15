# Chapter 5: **Implementing Place Autocomplete Search**

# Chapter 5: Implementing Place Autocomplete Search

Welcome back! In the previous chapters, we set up our basic Google Map and learned how to display it and potentially add markers. While seeing a static map is useful, a common requirement for map applications is the ability to search for specific locations. Manually entering coordinates isn't user-friendly.

In this chapter, we will integrate Google's Place Autocomplete service to provide a search bar that helps users find addresses and points of interest easily. We'll add a new component for the search bar and connect it to our main map page (`app/page.tsx`) to update the map view based on the user's selection.

## Why Place Autocomplete?

Google's Place Autocomplete service is a powerful tool that provides predictions for places (locations, businesses, points of interest) as the user types. This significantly improves the user experience by:

1.  **Reducing typing:** Users don't need to type the full address.
2.  **Minimizing errors:** Predictions help avoid typos and incorrect addresses.
3.  **Providing structured data:** When a user selects a prediction, the service returns detailed information about the place, including its exact latitude and longitude, which is crucial for centering our map.

## Prerequisites: Enabling the Places API

Before we can use Place Autocomplete, you need to ensure the **Places API** is enabled for your Google Cloud project where you obtained your API key.

Additionally, when loading the Google Maps JavaScript API script, you need to include the `libraries=places` parameter. Our existing setup likely uses `useLoadScript` from `@react-google-maps/api`. We just need to add this parameter to the `googleMapsApiKey` object passed to it.

Open `app/page.tsx` and modify the `useLoadScript` call:

```typescript
// app/page.tsx
// ... other imports

const { isLoaded } = useLoadScript({
  googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY as string,
  libraries: ['places'], // <--- Add this line
});

// ... rest of the component
```

Adding `'places'` to the `libraries` array ensures that the necessary code for the Places API, including Autocomplete, is loaded by the Google Maps script.

## The `PlacesAutocomplete` Component

Based on our repository structure analysis, we have a dedicated component located at `app/components/PlacesAutocomplete.tsx`. This component's responsibility is to handle the search input field and interact with the Google Place Autocomplete service.

While the detailed implementation of `PlacesAutocomplete.tsx` might vary (it could use a library like `react-google-autocomplete` or `react-places-autocomplete`, or interact directly with the Google Maps JavaScript API), its core function from the perspective of `app/page.tsx` is to:

1.  Render a text input field.
2.  Listen for user input.
3.  Fetch place predictions based on the input using the Google Places API.
4.  Display these predictions to the user (often as a dropdown list).
5.  When the user selects a prediction, retrieve the full place details (including coordinates).
6.  **Crucially:** Communicate the selected place data back to its parent component (`app/page.tsx`).

To achieve this communication, `PlacesAutocomplete.tsx` will accept a callback function as a prop. Let's call this prop `onPlaceSelect`. When a place is successfully selected by the user within the `PlacesAutocomplete` component, it will call this `onPlaceSelect` function, passing the selected place object as an argument.

## Integrating Autocomplete into `app/page.tsx`

Now, let's integrate the `PlacesAutocomplete` component into our main map page and handle the selected place data.

We need to:

1.  Import the `PlacesAutocomplete` component.
2.  Define a state management strategy to hold the map's center and the marker's position, as these will change based on the search result. (Based on the context, `center` and `markerPosition` state likely already exist).
3.  Create a function in `app/page.tsx` that will be triggered when a place is selected (`onPlaceSelect`). This function will receive the selected place data.
4.  Inside this function, extract the latitude and longitude from the selected place data.
5.  Update the `center` and `markerPosition` state variables with the new coordinates.
6.  Render the `PlacesAutocomplete` component in the JSX, passing the handling function as the `onPlaceSelect` prop.

Let's modify `app/page.tsx`:

```typescript
// app/page.tsx
'use client'; // Ensure this is a Client Component

import { useState, useMemo, useCallback } from 'react';
import { GoogleMap, MarkerF, useLoadScript, Libraries } from '@react-google-maps/api';
import PlacesAutocomplete from './components/PlacesAutocomplete'; // Import the new component

// Define the required libraries for useLoadScript
const libraries: Libraries = ['places'];

// Define the map container style and options
const mapContainerStyle = {
  width: '100%',
  height: '90vh', // Adjust height as needed
};

const defaultCenter = {
  lat: 34.0522, // Default: Los Angeles coordinates
  lng: -118.2437,
};

const mapOptions = {
  disableDefaultUI: true, // Optional: disable default map controls
  zoomControl: true,
};

export default function Home() {
  const { isLoaded } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY as string,
    libraries: libraries, // Use the defined libraries array
  });

  // State for map center and marker position
  const [center, setCenter] = useState(defaultCenter);
  const [markerPosition, setMarkerPosition] = useState(defaultCenter);
  const [map, setMap] = useState<google.maps.Map | null>(null); // State to hold map instance

  // Callback for when a place is selected from the autocomplete
  const handlePlaceSelect = useCallback((place: google.maps.places.PlaceResult | null) => {
    if (place && place.geometry && place.geometry.location) {
      const newPosition = {
        lat: place.geometry.location.lat(),
        lng: place.geometry.location.lng(),
      };
      console.log("Selected Place Coordinates:", newPosition); // Log the coordinates

      // Update the center and marker position
      setCenter(newPosition);
      setMarkerPosition(newPosition);

      // Optional: Pan the map to the new location smoothly
      if (map) {
        map.panTo(newPosition);
        map.setZoom(15); // Optional: set a specific zoom level after searching
      }
    } else {
      console.error("Selected place has no geometry or location.");
    }
  }, [map]); // Depend on the map instance to use panTo

  // Optional: Callback for when the map loads
  const onLoad = useCallback(function callback(map: google.maps.Map) {
    setMap(map); // Store the map instance
    // Optional: Do something when the map loads, like fitting bounds
  }, []);

  // Optional: Callback for when the map unloads
  const onUnmount = useCallback(function callback(map: google.maps.Map) {
    setMap(null); // Clear the map instance on unmount
  }, []);


  if (!isLoaded) {
    return <div>Loading Map...</div>;
  }

  return (
    <div className="relative flex flex-col items-center"> {/* Use relative positioning for the container */}
      {/* Render the PlacesAutocomplete component */}
      {/* Position it absolutely over the map or place it above */}
      <div className="absolute top-4 z-10 w-1/2 max-w-md"> {/* Example positioning */}
         <PlacesAutocomplete onPlaceSelect={handlePlaceSelect} />
      </div>

      <GoogleMap
        mapContainerStyle={mapContainerStyle}
        center={center} // Use the state variable for center
        zoom={10} // Default zoom level
        options={mapOptions}
        onLoad={onLoad} // Attach onLoad handler
        onUnmount={onUnmount} // Attach onUnmount handler
      >
        {/* Add a Marker at the selected/default position */}
        <MarkerF position={markerPosition} /> {/* Use the state variable for marker position */}
      </GoogleMap>
    </div>
  );
}
```

**Explanation of Changes:**

1.  **`'use client';`**: Ensure the component is marked as a client component, as map interactions and state management happen in the browser.
2.  **Import `PlacesAutocomplete`**: We import the component from its path `./components/PlacesAutocomplete`.
3.  **`libraries: ['places']`**: Added `'places'` to the `libraries` array passed to `useLoadScript`.
4.  **`center` and `markerPosition` State**: We use `useState` to manage the map's center and the marker's position. Initially, they are set to `defaultCenter`.
5.  **`map` State**: Added state to hold the `google.maps.Map` instance itself. This is useful for directly interacting with the map object, like using `map.panTo()`.
6.  **`onLoad` and `onUnmount` Callbacks**: Added handlers to get and set the map instance when the map component loads and unloads.
7.  **`handlePlaceSelect` Function**:
    *   This function is defined using `useCallback` to prevent unnecessary re-creations.
    *   It takes one argument, `place`, which is the object returned by the Autocomplete service when a place is selected. The type hint `google.maps.places.PlaceResult | null` is used for clarity.
    *   It checks if the `place` object and its `geometry` and `location` properties exist (this is important as sometimes place data might be incomplete).
    *   It extracts the latitude and longitude using `place.geometry.location.lat()` and `place.geometry.location.lng()`.
    *   It updates both the `center` and `markerPosition` state variables using `setCenter` and `setMarkerPosition`. This moves the map view and the marker to the selected location.
    *   It optionally uses `map.panTo(newPosition)` and `map.setZoom(15)` to smoothly animate the map transition and zoom in on the selected location, improving the user experience.
8.  **Rendering `PlacesAutocomplete`**:
    *   We render the `<PlacesAutocomplete />` component.
    *   We pass our `handlePlaceSelect` function to the `onPlaceSelect` prop. This establishes the communication channel from the child component (`PlacesAutocomplete`) back to the parent (`app/page.tsx`).
    *   We've wrapped the `PlacesAutocomplete` component in a `div` with some basic styling (`absolute`, `top-4`, `z-10`, `w-1/2`, `max-w-md`) to position it over the map. You can adjust this styling based on your layout needs.
9.  **`GoogleMap` and `MarkerF` Props**: Ensured that the `center` prop of `GoogleMap` and the `position` prop of `MarkerF` are bound to our state variables (`center` and `markerPosition`), so they automatically update when the state changes after a place selection.

Now, when a user types into the search box provided by `PlacesAutocomplete` and selects a result, the `handlePlaceSelect` function in `app/page.tsx` will run, updating the map's center and the marker's location.

*(Note: The actual implementation of `app/components/PlacesAutocomplete.tsx` is not shown here as it was not provided in the context, but the code above demonstrates how `app/page.tsx` interacts with it assuming it provides an `onPlaceSelect` prop that returns place result data.)*

## Conclusion

By adding the `PlacesAutocomplete` component and connecting its output to our map's state in `app/page.tsx`, we've successfully implemented a search feature. Users can now easily find locations using a familiar search interface, and the map will automatically update to show the selected place. This is a significant step in building a user-friendly map application.

In the next chapter, we might explore adding more interactivity, such as allowing users to click on the map to place markers or fetch information about a location.