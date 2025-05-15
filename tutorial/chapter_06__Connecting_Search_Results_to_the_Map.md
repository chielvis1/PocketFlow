# Chapter 6: **Connecting Search Results to the Map**

```markdown
# Chapter 6: Connecting Search Results to the Map

Welcome back! In the previous chapter, we successfully integrated the Google Places Autocomplete functionality, allowing users to search for locations and get a list of suggestions. However, selecting a place didn't actually *do* anything on our map yet.

The goal of this chapter is to bridge that gap. We will take the selected place's location data from the autocomplete component and use it to update the map's view – specifically, centering the map on the chosen location and placing a marker there.

## The Challenge: Communicating Between Components

Our `PlacesAutocomplete` component handles the search input and results, while our `app/page.tsx` file holds the state for the map and renders both the map and the autocomplete. For the map to react to a selection in the autocomplete component, these two parts need to communicate.

The standard React way to handle this kind of communication, where a child component (like `PlacesAutocomplete`) needs to send data *up* to a parent component (`app/page.tsx`), is using **callback functions passed as props**.

The parent (`app/page.tsx`) will define a function that knows how to handle a selected place. It will then pass this function down to the child (`PlacesAutocomplete`) as a prop. When the child successfully selects a place, it will call this function, passing the selected place data back up.

## Implementing the Connection in `app/page.tsx`

First, let's modify `app/page.tsx` to handle the incoming selected place data and update the map's state.

We need two pieces of state:
1.  The current center of the map. This will initially be our default location but will update when a place is selected.
2.  The position of the marker we want to display. This will be `null` initially and set to the selected place's coordinates after a selection.

We'll also create the callback function that `PlacesAutocomplete` will call.

Here's how we'll update `app/page.tsx`:

```typescript
'use client';

import { useState, useMemo, useCallback } from 'react';
import { GoogleMap, MarkerF, useLoadScript } from '@react-google-maps/api';
import PlacesAutocomplete from './components/PlacesAutocomplete'; // Import the Autocomplete component

type LatLngLiteral = google.maps.LatLngLiteral;
type Place = google.maps.places.Place; // Assuming you might need the full Place type later

// Default center location (e.g., San Francisco)
const defaultCenter = { lat: 37.7749, lng: -122.4194 };

// Optional: Define libraries needed for Google Maps API
const libraries: (keyof google.maps.drawing.OverlayType | keyof google.maps.places.PlacesServiceStatus)[] = ['places'];

export default function Home() {
  // Load Google Maps script with API key and libraries
  const { isLoaded } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY as string,
    libraries: libraries, // Use the libraries array
  });

  // State for the map's current center
  const [mapCenter, setMapCenter] = useState<LatLngLiteral>(defaultCenter);

  // State for the position of the selected place marker
  const [selectedPlacePosition, setSelectedPlacePosition] = useState<LatLngLiteral | null>(null);

  // Memoize map options to prevent unnecessary re-renders
  const mapOptions = useMemo<google.maps.MapOptions>(
    () => ({
      disableDefaultUI: true, // Disable default controls for a cleaner look
      clickableIcons: false, // Disable clickable icons on the map
      zoomControl: true,
      streetViewControl: false,
      fullscreenControl: false,
      mapTypeControl: false,
    }),
    []
  );

  // Callback function to handle place selection from Autocomplete
  const handlePlaceSelect = useCallback((place: Place | null) => {
    if (place && place.geometry && place.geometry.location) {
      const newPosition: LatLngLiteral = {
        lat: place.geometry.location.lat(),
        lng: place.geometry.location.lng(),
      };
      console.log('Selected place coordinates:', newPosition); // Log the coordinates
      setMapCenter(newPosition); // Update map center
      setSelectedPlacePosition(newPosition); // Set marker position
    } else {
       // Handle case where place data is incomplete or null (e.g., user clears input)
       console.log('Place data incomplete or null');
       // Optionally reset state if needed, e.g., clear marker
       setSelectedPlacePosition(null);
    }
  }, []); // Empty dependency array means this function is created once

  if (!isLoaded) {
    return <div>Loading Map...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw' }}>
      {/* Autocomplete component, now passing the callback function */}
      <div style={{ padding: '10px', zIndex: 1 }}> {/* Add padding and zIndex to keep it above map */}
        <PlacesAutocomplete onPlaceSelect={handlePlaceSelect} />
      </div>

      {/* Google Map component */}
      <div style={{ flexGrow: 1 }}> {/* Allow map to take remaining space */}
        <GoogleMap
          mapContainerStyle={{ width: '100%', height: '100%' }}
          options={mapOptions}
          zoom={14} // Adjust zoom level as needed
          center={mapCenter} // Map center is now controlled by state
        >
          {/* Render Marker only if a place has been selected */}
          {selectedPlacePosition && (
            <MarkerF position={selectedPlacePosition} />
          )}
        </GoogleMap>
      </div>
    </div>
  );
}

```

**Key Changes in `app/page.tsx`:**

1.  **Import `useCallback`:** Needed for memoizing the `handlePlaceSelect` function.
2.  **State Variables:**
    *   `mapCenter`: Initialized with `defaultCenter`. This state variable is now bound to the `center` prop of the `GoogleMap`.
    *   `selectedPlacePosition`: Initialized to `null`. This state variable will hold the coordinates for the marker.
3.  **`handlePlaceSelect` Function:**
    *   This function is defined using `useCallback` to ensure it's stable across renders.
    *   It takes a `place` object (or `null`) as an argument.
    *   It checks if the `place` and its `geometry.location` are valid.
    *   It extracts the latitude and longitude using `place.geometry.location.lat()` and `place.geometry.location.lng()`. Note that these are functions, not properties, on the Google Maps `LatLng` object.
    *   It updates both `mapCenter` and `selectedPlacePosition` state variables using the extracted coordinates.
    *   Includes basic handling for incomplete/null data.
4.  **Passing the Prop:** The `handlePlaceSelect` function is passed down to the `PlacesAutocomplete` component via the `onPlaceSelect` prop.
5.  **Updating Map Center:** The `center` prop of the `GoogleMap` is now set to the `mapCenter` state.
6.  **Adding the Marker:** A `MarkerF` component is conditionally rendered. It only appears if `selectedPlacePosition` is not `null`. Its `position` prop is bound to the `selectedPlacePosition` state.

## Updating the Autocomplete Component (`PlacesAutocomplete.tsx`)

Now, we need to modify the `PlacesAutocomplete` component to accept the `onPlaceSelect` prop and call it when a place is successfully selected and its details are fetched.

```typescript
import React from 'react';
import usePlacesAutocomplete, { getGeocode, getLatLng } from 'use-places-autocomplete';
import {
  Combobox,
  ComboboxInput,
  ComboboxPopover,
  ComboboxList,
  ComboboxOption,
} from '@reach/combobox';
import '@reach/combobox/styles.css'; // Import combobox styles

// Define the type for the prop that will be passed down
interface PlacesAutocompleteProps {
  onPlaceSelect: (place: google.maps.places.Place | null) => void;
}

const PlacesAutocomplete: React.FC<PlacesAutocompleteProps> = ({ onPlaceSelect }) => {
  // usePlacesAutocomplete hook for handling search input and fetching suggestions
  const {
    ready, // boolean: whether the hook is ready (script loaded, etc.)
    value, // string: the current value of the input field
    suggestions: { status, data }, // object: suggestions data { status: 'OK' | 'ZERO_RESULTS', data: [...] }
    setValue, // function: to update the input value
    clearSuggestions, // function: to clear the suggestions list
  } = usePlacesAutocomplete({
    requestOptions: {
      /* Define search options here */
      // For example, restrict results to a specific country:
      // componentRestrictions: { country: 'us' },
    },
    debounce: 300, // Delay before fetching suggestions
  });

  // Function to handle selection of a suggestion
  const handleSelect = async (address: string) => {
    setValue(address, false); // Set the input value to the selected address, don't fetch suggestions again
    clearSuggestions(); // Clear the suggestions list

    try {
      // Fetch geocode data for the selected address
      const results = await getGeocode({ address });

      // Check if results contain place details
      if (results && results[0]) {
         // The results array from getGeocode for place_id requests
         // often contains the full Place details in the first element.
         // We pass the entire result object back.
         console.log('Selected Place Details:', results[0]); // Log the details
         onPlaceSelect(results[0] as google.maps.places.Place); // Call the callback with the selected place details
      } else {
         console.warn('No place details found for selected address:', address);
         onPlaceSelect(null); // Indicate no place data was found
      }

      // // Alternative: If you only needed LatLng and not full Place details:
      // const { lat, lng } = await getLatLng(results[0]);
      // console.log('Selected LatLng:', { lat, lng });
      // // If you only needed LatLng, you would call onPlaceSelect({ geometry: { location: { lat: () => lat, lng: () => lng } } });
      // // but passing the full Place object is more flexible.

    } catch (error) {
      console.error('Error fetching place details:', error);
      onPlaceSelect(null); // Indicate an error occurred
    }
  };

  return (
    <Combobox onSelect={handleSelect}>
      <ComboboxInput
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={!ready} // Disable input until hook is ready
        placeholder="Search for a place..."
        style={{ width: '100%', padding: '10px', boxSizing: 'border-box' }} // Basic styling
      />
      <ComboboxPopover>
        <ComboboxList>
          {/* Render suggestions if status is OK */}
          {status === 'OK' &&
            data.map(({ place_id, description }) => (
              <ComboboxOption key={place_id} value={description} />
            ))}
           {/* Optional: Handle ZERO_RESULTS or other statuses */}
           {status === 'ZERO_RESULTS' && (
               <div style={{ padding: '5px' }}>No results found</div>
           )}
        </ComboboxList>
      </ComboboxPopover>
    </Combobox>
  );
};

export default PlacesAutocomplete;
```

**Key Changes in `PlacesAutocomplete.tsx`:**

1.  **Define Prop Type:** Added an interface `PlacesAutocompleteProps` to define the expected `onPlaceSelect` prop, which is a function that takes a `Place | null` and returns `void`.
2.  **Destructure Prop:** The `onPlaceSelect` prop is destructured from the component's props.
3.  **Call the Callback:** Inside the `handleSelect` function, after successfully fetching the place details using `getGeocode`, the `onPlaceSelect` prop is called, passing the fetched `results[0]` (which contains the place details) back to the parent.
4.  **Error Handling:** Added basic error handling in the `try...catch` block and calls `onPlaceSelect(null)` if an error occurs or no valid place data is found.

## Putting It All Together: The Data Flow

Let's trace the flow of events when a user selects a place:

1.  The user types into the search input, `usePlacesAutocomplete` fetches suggestions, and the `ComboboxOptions` are displayed.
2.  The user selects an option from the dropdown.
3.  The `onSelect` handler of the `Combobox` triggers the `handleSelect` function within `PlacesAutocomplete.tsx`.
4.  `handleSelect` updates the input value, clears suggestions, and calls `getGeocode` (which implicitly uses the Place ID obtained from the suggestion) to fetch detailed information about the selected place.
5.  Once `getGeocode` returns the place details, `handleSelect` calls the `onPlaceSelect` prop, passing the place object (`results[0]`).
6.  The `onPlaceSelect` function in `app/page.tsx` (which is `handlePlaceSelect`) receives the place object.
7.  `handlePlaceSelect` extracts the latitude and longitude from `place.geometry.location`.
8.  `handlePlaceSelect` updates the `mapCenter` and `selectedPlacePosition` state variables using `setMapCenter` and `setSelectedPlacePosition`.
9.  React detects the state changes in `app/page.tsx` and triggers a re-render.
10. During the re-render, the `GoogleMap` component receives the new `mapCenter` value for its `center` prop, causing the map to pan and zoom to the new location.
11. The `MarkerF` component is now rendered because `selectedPlacePosition` is no longer `null`, and its `position` prop is set to the selected coordinates, placing a marker on the map.

This establishes a clear, unidirectional data flow from the child (`PlacesAutocomplete`) up to the parent (`app/page.tsx`) and then back down to the rendering components (`GoogleMap`, `MarkerF`).

## Conclusion

Congratulations! You have successfully connected the search functionality to the map. Users can now search for locations, and upon selection, the map will automatically center on that location and display a marker. This significantly enhances the usability of your application, making it a truly interactive mapping tool.

In the next chapter, we might explore adding more interactivity, perhaps displaying information about the selected place in an info window or handling different types of map actions.

```