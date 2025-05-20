# Chapter 5: **State Management and Parent-Child Communication in React**  

# Chapter 5: State Management and Parent-Child Communication in React

In this chapter, we will explore how **state management** and **parent-child communication** work together in the `page.tsx` file of our Next.js + Google Maps API project. Specifically, we will focus on how the location state (`lat` / `lng`) is managed and updated based on user interactions, and how child components notify the parent of changes through callback props.

Understanding these React concepts is essential for building interactive UIs that respond dynamically to user input, such as updating a map when a new place is selected.

---

## 5.1 Introduction to State Management in React

React components can maintain their own internal state using the `useState` hook. This state controls what the component renders and can change over time in response to user actions or other events.

In our `page.tsx` file, we keep track of the selected location’s coordinates (`lat` and `lng`) in state. This allows us to:

- Render the map centered on the current location.
- Update the map view whenever the user selects a new location.

---

## 5.2 The `page.tsx` Component: Managing Location State

Let's look at the core of how `page.tsx` manages the location state:

```tsx
import { useState } from "react";
import PlacesAutocomplete from "./PlacesAutocomplete";
import Map from "./Map";

export default function Page() {
  // State to hold the current location coordinates
  const [location, setLocation] = useState<{ lat: number; lng: number }>({
    lat: 37.7749,
    lng: -122.4194, // Default: San Francisco coordinates
  });

  // Callback to update location state from child component
  const handleLocationSelect = (newLocation: { lat: number; lng: number }) => {
    setLocation(newLocation);
  };

  return (
    <div>
      {/* Pass callback prop to child */}
      <PlacesAutocomplete onSelect={handleLocationSelect} />

      {/* Pass location state to Map for rendering */}
      <Map center={location} />
    </div>
  );
}
```

### Explanation

- We declare a `location` state variable using `useState`, initializing it with default coordinates.
- The `handleLocationSelect` function updates this state when called.
- `PlacesAutocomplete` is a child component that allows the user to search and select places.
- We pass `handleLocationSelect` as a prop named `onSelect` to `PlacesAutocomplete`.
- When `PlacesAutocomplete` detects a location selection, it calls this callback with the new coordinates.
- The state update triggers a re-render of `page.tsx`, which in turn passes the updated location to the `Map` component to update the map view.

---

## 5.3 Lifting State Up: Why Manage Location in `page.tsx`?

In React, **lifting state up** means moving shared state to the closest common ancestor of components that need it.

Here:

- Both `PlacesAutocomplete` (child) and `Map` (another child) depend on the selected location.
- To synchronize them, the location state lives in their common parent: `page.tsx`.
- `PlacesAutocomplete` only has the responsibility to notify `page.tsx` of the new location via a callback.
- `page.tsx` holds the authoritative location state and passes it down to `Map`.

This pattern ensures a single source of truth, avoids duplication, and keeps components reusable and focused on their own concerns.

---

## 5.4 Callback Props: Enabling Child to Parent Communication

React’s data flow is **unidirectional** (top-down). Parents pass data to children via props, but children cannot directly change parent state. To communicate changes back up, React uses **callback props**.

### How It Works in Our Example

- The parent (`page.tsx`) passes a function (`handleLocationSelect`) as a prop to the child (`PlacesAutocomplete`).
- When the user selects a location inside `PlacesAutocomplete`, it calls this function, passing the new coordinates.
- This triggers a state update in the parent, which causes a re-render and updates all dependent components.

### Example snippet from `PlacesAutocomplete`:

```tsx
type PlacesAutocompleteProps = {
  onSelect: (location: { lat: number; lng: number }) => void;
};

function PlacesAutocomplete({ onSelect }: PlacesAutocompleteProps) {
  // ... some autocomplete logic, e.g., Google Places API

  function handlePlaceSelect(place: any) {
    // Extract coordinates from the selected place
    const lat = place.geometry.location.lat();
    const lng = place.geometry.location.lng();

    // Notify parent of new location
    onSelect({ lat, lng });
  }

  // Render autocomplete UI and bind handlePlaceSelect to selection event
  return (
    <input type="text" /* autocomplete search UI */ />
    // ...
  );
}
```

---

## 5.5 Reactivity and Component Re-rendering

When the state in `page.tsx` changes via `setLocation`, React triggers a re-render of `page.tsx` and all its children that depend on the changed state.

- The `Map` component receives the updated `center` prop with new coordinates.
- `Map` updates its display accordingly, showing the map centered on the new location.
- This reactive update flow happens seamlessly due to React’s virtual DOM diffing and efficient rendering.

---

## 5.6 Summary of Key Concepts

| Concept                | Description                                                                                   | Example in This Project                      |
|------------------------|-----------------------------------------------------------------------------------------------|---------------------------------------------|
| `useState`             | React hook to hold component state and update it over time.                                   | `const [location, setLocation] = useState(...)` |
| Lifting State Up       | Moving shared state to the closest common ancestor to synchronize multiple children.           | `location` state lives in `page.tsx`         |
| Callback Props         | Passing functions from parent to child to enable children to notify parents of changes.       | `onSelect={handleLocationSelect}` passed to `PlacesAutocomplete` |
| Reactivity & Re-render | State updates cause React to re-render affected components with new data.                      | `Map` updates when `location` changes       |

---

## 5.7 Conclusion

In this chapter, we learned how `page.tsx` effectively manages the location state (`lat/lng`) using React’s `useState` hook. By lifting the location state up to the parent component, it synchronizes the user selection in `PlacesAutocomplete` with the map rendering in `Map`.

The callback prop pattern enables child components to notify parents of user actions, maintaining React’s unidirectional data flow while allowing for dynamic, responsive UI updates.

Mastering these state management and communication patterns is essential for building scalable React applications that integrate complex interactive features like maps and location search.

---

In the next chapter, we will dive deeper into enhancing the user experience by adding loading states and error handling around the location search and map rendering processes.