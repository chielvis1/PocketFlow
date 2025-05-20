# Chapter 6: **Putting It All Together: Composing the Main Page UI**  

# Chapter 6: Putting It All Together: Composing the Main Page UI

In this chapter, we'll bring together the key pieces we've developed so far — the `PlacesAutocomplete` input component and the Google Map — into a cohesive main page UI inside `page.tsx`. You'll see how state, callbacks, and external components interact smoothly to provide a responsive and intuitive map search experience.

By the end, you’ll understand how to compose components, manage state and props effectively, and render UI dynamically based on user input and asynchronous data.

---

## 6.1 Introduction

Our goal is to create a seamless user experience where:

- Users can type a location in the autocomplete input.
- Suggestions appear dynamically as they type.
- Upon selecting a place, the map updates to center on that location.

This requires coordinating state changes, handling callbacks between components, and conditionally rendering UI elements. Let’s explore how this is achieved in the main page component.

---

## 6.2 Overview of `page.tsx`

The `page.tsx` file acts as the container and orchestrator of the UI. It imports and composes:

- **`PlacesAutocomplete`** — a controlled input component that fetches place suggestions.
- **Google Map component** — rendering the map centered on the selected location.

The component will:

- Maintain state for the selected location (coordinates and address).
- Pass down callbacks to update this state based on user interaction.
- Render the map with props derived from the current state.

---

## 6.3 Component Composition and State Management

### State Setup

Inside `page.tsx`, we define React state hooks to track:

- `selectedLocation`: an object holding latitude, longitude, and display name.
- Optionally, a loading or error state for better UX.

```tsx
import React, { useState } from 'react';
import PlacesAutocomplete from '../components/PlacesAutocomplete';
import Map from '../components/Map';

interface Location {
  lat: number;
  lng: number;
  address: string;
}

export default function HomePage() {
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);

  // ...
}
```

### Why use state here?

Because the main page needs to:

- React to user input from `PlacesAutocomplete`.
- Pass updated location data to the `Map` component.
- Trigger re-renders when the location changes.

### Passing Callbacks to Child Components

The `PlacesAutocomplete` component expects a callback prop (e.g., `onSelect`) to notify the parent when a user selects a suggestion.

```tsx
// Handler invoked when a place is selected
const handleSelect = (location: Location) => {
  setSelectedLocation(location);
};
```

This method updates the `selectedLocation` state, which in turn updates the map center.

---

## 6.4 Controlled Components and Prop Drilling

The autocomplete input is a **controlled component**, meaning its value is managed by React state. This ensures the UI stays in sync with the application state.

```tsx
<PlacesAutocomplete onSelect={handleSelect} />
```

`PlacesAutocomplete` internally manages its input value and suggestions, but informs the parent about user selections via `onSelect`.

Similarly, the `Map` component receives the current location as props:

```tsx
<Map center={selectedLocation ? { lat: selectedLocation.lat, lng: selectedLocation.lng } : defaultCenter} />
```

This pattern — passing data down and events up — is fundamental in React for predictable UI behavior.

---

## 6.5 Conditional Rendering Based on State

Initially, when no location is selected, the map can default to a general view (e.g., a world map or a city center).

```tsx
const defaultCenter = { lat: 40.7128, lng: -74.0060 }; // New York City
```

Within the render:

```tsx
<Map center={selectedLocation ? { lat: selectedLocation.lat, lng: selectedLocation.lng } : defaultCenter} />
```

This conditional logic ensures the user always sees a meaningful map.

---

## 6.6 Complete `page.tsx` Example

Here’s the full example putting it all together:

```tsx
'use client';

import React, { useState } from 'react';
import PlacesAutocomplete from '../components/PlacesAutocomplete';
import Map from '../components/Map';

interface Location {
  lat: number;
  lng: number;
  address: string;
}

export default function HomePage() {
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);

  const defaultCenter = { lat: 40.7128, lng: -74.0060 }; // Default to NYC

  const handleSelect = (location: Location) => {
    setSelectedLocation(location);
  };

  return (
    <main className="flex flex-col items-center p-4 space-y-6">
      <h1 className="text-2xl font-bold">Search for a Place</h1>

      {/* PlacesAutocomplete input */}
      <PlacesAutocomplete onSelect={handleSelect} />

      {/* Map component centered on selectedLocation or default */}
      <div className="w-full h-[400px]">
        <Map center={selectedLocation ? { lat: selectedLocation.lat, lng: selectedLocation.lng } : defaultCenter} />
      </div>
    </main>
  );
}
```

---

## 6.7 How This Works Together

- The user types into `PlacesAutocomplete`.
- Suggestions update dynamically inside that component.
- When a suggestion is clicked:
  - `PlacesAutocomplete` calls `onSelect` with the location details.
  - `HomePage` updates `selectedLocation` state.
- React re-renders `HomePage`, passing new coordinates to `Map`.
- `Map` recenters on the new location.

This tight coupling via state and props ensures a smooth and reactive UI.

---

## 6.8 Summary

In this chapter, we:

- Composed the main page UI by integrating `PlacesAutocomplete` and `Map`.
- Managed shared state in the parent component to coordinate data flow.
- Passed callbacks and props for controlled, responsive components.
- Used conditional rendering to handle initial and updated map views.

This pattern of component composition and state management forms the backbone of interactive React applications — a skill you can now confidently apply to extend or customize your map search experience.

---

In the next chapter, we’ll explore enhancing the user experience with loading states, error handling, and UI polish to make the app production-ready.