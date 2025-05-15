# Chapter 7: **Styling the Application**

```markdown
# Chapter 7: Styling the Application

So far, we've built a functional map application that allows users to search for locations. While functionality is key, the user interface's appearance significantly impacts the user experience. In this chapter, we'll focus on styling our application to make it visually appealing and more user-friendly.

For this tutorial, we'll assume you are using Tailwind CSS, which is a popular utility-first CSS framework commonly integrated with Next.js projects. Tailwind allows us to rapidly style our components by adding pre-defined classes directly to our HTML/JSX elements.

If your project isn't set up with Tailwind, you would typically install it and configure it according to the official Tailwind CSS documentation for Next.js.

## 7.1 Styling the Main Layout

Let's start by styling the main container in our `app/page.tsx` file. We want the application to take up the full height of the viewport and arrange the search input and the map vertically with some spacing.

We'll add Tailwind classes to the main `div` element that wraps the `PlacesAutocomplete` component and the map container.

```typescript jsx
// app/page.tsx
'use client';

import { useState, useMemo, useCallback, useRef } from 'react';
import { GoogleMap, MarkerF, useLoadScript } from '@react-google-maps/api';
import PlacesAutocomplete from './components/PlacesAutocomplete';

type Location = { lat: number; lng: number };

// Define the libraries needed for the Google Maps API
const libraries: (
  | 'places'
  | 'drawing'
  | 'geometry'
  | 'localContext'
  | 'visualization'
)[] = ['places'];

export default function Home() {
  // Load the Google Maps script using the API key from environment variables
  const { isLoaded } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY as string,
    libraries: libraries,
  });

  // State to hold the current location shown on the map
  const [currentLocation, setCurrentLocation] = useState<Location | null>(null);

  // Memoize the default center location to avoid re-creating it
  // This is a placeholder location, ideally you might get user's current location
  const center = useMemo<Location>(
    () => ({ lat: 43.653225, lng: -79.383186 }), // Example: Toronto coordinates
    []
  );

  // Ref for the map instance to access its methods (e.g., panTo)
  const mapRef = useRef<GoogleMap | null>(null);

  // Callback function when the map loads
  const onLoad = useCallback(
    (map: any) => {
      mapRef.current = map;
    },
    []
  );

  // Function to handle location selection from the autocomplete
  const handleLocationSelect = useCallback(
    (lat: number, lng: number) => {
      const newLocation = { lat, lng };
      setCurrentLocation(newLocation);

      // If the map is loaded, pan to the selected location
      if (mapRef.current) {
        mapRef.current.panTo(newLocation);
        mapRef.current.setZoom(15); // Set a reasonable zoom level
      }
    },
    [] // Dependencies
  );

  // Show a loading message while the script is loading
  if (!isLoaded) {
    return <div>Loading Map...</div>;
  }

  return (
    // Add Tailwind classes for flex column layout, full height, padding, and gap
    <div className="flex flex-col h-screen p-4 gap-4">
      {/* Autocomplete component */}
      <PlacesAutocomplete onLocationSelect={handleLocationSelect} />

      {/* Map container - We will make this take up the remaining space */}
      <div className="flex-grow"> {/* This div will expand to fill available height */}
        <GoogleMap
          // Style for the map container itself (fills its parent div)
          mapContainerStyle={{ width: '100%', height: '100%' }}
          center={currentLocation || center} // Use selected location or default center
          zoom={currentLocation ? 15 : 10} // Adjust zoom based on whether a location is selected
          onLoad={onLoad} // Assign the onLoad callback
        >
          {/* Render a marker if a location is selected */}
          {currentLocation && <MarkerF position={currentLocation} />}
        </GoogleMap>
      </div>
    </div>
  );
}
```

**Explanation:**

*   `className="flex flex-col h-screen p-4 gap-4"`:
    *   `flex`: Makes the `div` a flex container.
    *   `flex-col`: Arranges flex items (the autocomplete and the map container) vertically.
    *   `h-screen`: Sets the height of the `div` to 100% of the viewport height.
    *   `p-4`: Adds padding (spacing) of 1rem (by default) on all sides.
    *   `gap-4`: Adds a gap of 1rem between flex items.
*   We also wrapped the `GoogleMap` component in another `div` with `className="flex-grow"`. In a flex container with `flex-col`, `flex-grow` makes this element take up all the remaining vertical space after the other elements (the autocomplete input) have taken their required space.

## 7.2 Sizing the Map

The `GoogleMap` component itself needs a defined size to render correctly. While its parent container is now set up to provide the available space using `flex-grow`, the `GoogleMap` component requires the size to be passed via the `mapContainerStyle` prop.

We've already added this in the previous step, but let's highlight it:

```typescript jsx
<GoogleMap
  // Style for the map container itself (fills its parent div)
  mapContainerStyle={{ width: '100%', height: '100%' }}
  // ... other props
>
  {/* ... markers */}
</GoogleMap>
```

**Explanation:**

*   `mapContainerStyle={{ width: '100%', height: '100%' }}`: This prop takes a JavaScript object representing inline CSS styles for the internal container that the Google Map renders into. By setting `width: '100%'` and `height: '100%'`, we instruct the map to fill the entire area of its parent `div` (the one with `flex-grow`).

## 7.3 Styling the Autocomplete Input

Now, let's style the input field within the `PlacesAutocomplete` component to make it look like a standard form input.

We'll add Tailwind classes to the `<input>` element in `app/components/PlacesAutocomplete.tsx`.

```typescript jsx
// app/components/PlacesAutocomplete.tsx
import usePlacesAutocomplete, {
  getGeocode,
  getLatLng,
} from 'use-places-autocomplete';
import {
  Combobox,
  ComboboxInput,
  ComboboxPopover,
  ComboboxList,
  ComboboxOption,
} from '@reach/combobox';
import '@reach/combobox/styles.css'; // Basic styles for reach/combobox

type PlacesAutocompleteProps = {
  onLocationSelect: (lat: number, lng: number) => void;
};

export default function PlacesAutocomplete({
  onLocationSelect,
}: PlacesAutocompleteProps) {
  // Hook to get autocomplete suggestions and input value
  const {
    ready, // boolean: is the service ready?
    value, // string: the current input value
    suggestions: { status, data }, // object: suggestions data { status, data }
    setValue, // function: to set the input value
    clearSuggestions, // function: to clear suggestions
  } = usePlacesAutocomplete({
    requestOptions: {
      /* Define search scope here */
    },
    debounce: 300, // delay in ms before fetching suggestions
  });

  // Function to handle selection of a place from suggestions
  const handleSelect = async (address: string) => {
    setValue(address, false); // Set input value without fetching new suggestions
    clearSuggestions(); // Clear suggestions

    try {
      // Get geocode data for the selected address
      const results = await getGeocode({ address });
      // Get latitude and longitude from the geocode results
      const { lat, lng } = getLatLng(results[0]);
      // Call the parent component's callback with the selected coordinates
      onLocationSelect(lat, lng);
    } catch (error) {
      console.error('Error: ', error);
    }
  };

  return (
    // Combobox component from @reach/combobox
    <Combobox onSelect={handleSelect}>
      {/* Input field */}
      <ComboboxInput
        value={value} // Bind input value to hook's state
        onChange={(e) => setValue(e.target.value)} // Update hook's state on change
        disabled={!ready} // Disable input if service is not ready
        // Add Tailwind classes for styling
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="Search for a location..."
      />

      {/* Popover for suggestions */}
      <ComboboxPopover className="z-10 mt-1 bg-white border border-gray-300 rounded-md shadow-lg">
        {/* List of suggestions */}
        <ComboboxList>
          {/* Render suggestions only if status is OK */}
          {status === 'OK' &&
            data.map(({ place_id, description }) => (
              // Each suggestion as a ComboboxOption
              <ComboboxOption
                key={place_id}
                value={description}
                className="px-3 py-2 cursor-pointer hover:bg-gray-100" // Tailwind classes for options
              />
            ))}
        </ComboboxList>
      </ComboboxPopover>
    </Combobox>
  );
}
```

**Explanation:**

*   `className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"`:
    *   `w-full`: Makes the input take up the full width of its container.
    *   `px-3`: Adds horizontal padding (left and right).
    *   `py-2`: Adds vertical padding (top and bottom).
    *   `border border-gray-300`: Adds a standard grey border.
    *   `rounded-md`: Adds slightly rounded corners.
    *   `focus:outline-none`: Removes the default browser focus outline.
    *   `focus:ring-2 focus:ring-blue-500`: Adds a blue ring when the input is focused for better accessibility and visual feedback.
    *   `focus:border-transparent`: Makes the border transparent when focused to avoid doubling up with the ring.
*   We also added basic styling to the `ComboboxPopover` and `ComboboxOption` elements using Tailwind classes to give the suggestions list a clean look with borders, background colors, padding, and hover effects. Note the `z-10` class on the popover to ensure it appears above the map.

## 7.4 Putting it Together

With these changes, your application should now have a much cleaner and more structured layout. The search input will look like a standard form field, and the map will correctly size to fill the available space.

Here are the complete files with the styling applied:

**`app/page.tsx`:**

```typescript jsx
// app/page.tsx
'use client';

import { useState, useMemo, useCallback, useRef } from 'react';
import { GoogleMap, MarkerF, useLoadScript } from '@react-google-maps/api';
import PlacesAutocomplete from './components/PlacesAutocomplete';

type Location = { lat: number; lng: number };

const libraries: (
  | 'places'
  | 'drawing'
  | 'geometry'
  | 'localContext'
  | 'visualization'
)[] = ['places'];

export default function Home() {
  const { isLoaded } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY as string,
    libraries: libraries,
  });

  const [currentLocation, setCurrentLocation] = useState<Location | null>(null);

  const center = useMemo<Location>(
    () => ({ lat: 43.653225, lng: -79.383186 }), // Example: Toronto coordinates
    []
  );

  const mapRef = useRef<GoogleMap | null>(null);

  const onLoad = useCallback(
    (map: any) => {
      mapRef.current = map;
    },
    []
  );

  const handleLocationSelect = useCallback(
    (lat: number, lng: number) => {
      const newLocation = { lat, lng };
      setCurrentLocation(newLocation);

      if (mapRef.current) {
        mapRef.current.panTo(newLocation);
        mapRef.current.setZoom(15);
      }
    },
    []
  );

  if (!isLoaded) {
    return <div>Loading Map...</div>;
  }

  return (
    <div className="flex flex-col h-screen p-4 gap-4">
      <PlacesAutocomplete onLocationSelect={handleLocationSelect} />

      <div className="flex-grow">
        <GoogleMap
          mapContainerStyle={{ width: '100%', height: '100%' }}
          center={currentLocation || center}
          zoom={currentLocation ? 15 : 10}
          onLoad={onLoad}
        >
          {currentLocation && <MarkerF position={currentLocation} />}
        </GoogleMap>
      </div>
    </div>
  );
}
```

**`app/components/PlacesAutocomplete.tsx`:**

```typescript jsx
// app/components/PlacesAutocomplete.tsx
import usePlacesAutocomplete, {
  getGeocode,
  getLatLng,
} from 'use-places-autocomplete';
import {
  Combobox,
  ComboboxInput,
  ComboboxPopover,
  ComboboxList,
  ComboboxOption,
} from '@reach/combobox';
import '@reach/combobox/styles.css'; // Basic styles for reach/combobox

type PlacesAutocompleteProps = {
  onLocationSelect: (lat: number, lng: number) => void;
};

export default function PlacesAutocomplete({
  onLocationSelect,
}: PlacesAutocompleteProps) {
  const {
    ready,
    value,
    suggestions: { status, data },
    setValue,
    clearSuggestions,
  } = usePlacesAutocomplete({
    requestOptions: {
      /* Define search scope here */
    },
    debounce: 300,
  });

  const handleSelect = async (address: string) => {
    setValue(address, false);
    clearSuggestions();

    try {
      const results = await getGeocode({ address });
      const { lat, lng } = getLatLng(results[0]);
      onLocationSelect(lat, lng);
    } catch (error) {
      console.error('Error: ', error);
    }
  };

  return (
    <Combobox onSelect={handleSelect}>
      <ComboboxInput
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={!ready}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder="Search for a location..."
      />

      <ComboboxPopover className="z-10 mt-1 bg-white border border-gray-300 rounded-md shadow-lg">
        <ComboboxList>
          {status === 'OK' &&
            data.map(({ place_id, description }) => (
              <ComboboxOption
                key={place_id}
                value={description}
                className="px-3 py-2 cursor-pointer hover:bg-gray-100"
              />
            ))}
        </ComboboxList>
      </ComboboxPopover>
    </Combobox>
  );
}
```

## Conclusion

In this chapter, we successfully applied styling to our application using Tailwind CSS. We structured the main layout using flexbox to ensure the map takes up the available space and styled the autocomplete input to provide a better user experience. This demonstrates how utility-first CSS frameworks can quickly enhance the visual appearance of your React/Next.js components. You can further customize the styles by exploring more Tailwind classes or adding custom CSS rules if needed.