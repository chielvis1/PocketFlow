# Chapter 4: **Implementing Places Autocomplete Input Component**  

# Chapter 4: Implementing Places Autocomplete Input Component

In this chapter, we will build a reusable `PlacesAutocomplete` input component that integrates the Google Places Autocomplete functionality using the `use-places-autocomplete` custom hook. This component will manage the input state, display location suggestions dynamically, and follow accessibility best practices. We will also design the component to communicate with parent components through callback props, enabling flexible and scalable usage across the application.

---

## Table of Contents

- [Introduction](#introduction)  
- [Setting Up `use-places-autocomplete`](#setting-up-use-places-autocomplete)  
- [Managing Controlled Input State](#managing-controlled-input-state)  
- [Rendering Suggestions and Handling Selection](#rendering-suggestions-and-handling-selection)  
- [Accessibility Considerations with `useId`](#accessibility-considerations-with-useid)  
- [Callback Props for Parent Communication](#callback-props-for-parent-communication)  
- [Putting It All Together: Complete Component Example](#putting-it-all-together-complete-component-example)  
- [Conclusion](#conclusion)  

---

## Introduction

Autocomplete inputs for places are a common UX pattern in modern web applications, especially those dealing with maps, delivery, or travel features. While Google Maps Places API provides rich autocomplete functionality, integrating it efficiently and accessibly in React requires careful state management and architectural decisions.

The `PlacesAutocomplete` component we build here will:

- Use the `use-places-autocomplete` hook to manage API logic and suggestions  
- Manage the input as a controlled component for predictable behavior  
- Display dynamic suggestions with keyboard and screen reader accessibility  
- Allow parent components to respond to user selections via callbacks  

Let’s dive in!

---

## Setting Up `use-places-autocomplete`

`use-places-autocomplete` is a handy hook that abstracts away the complexity of interacting with the Google Places Autocomplete API. It manages fetching suggestions based on input value and exposes helpful functions and data.

To start, install the package (if not already done):

```bash
npm install use-places-autocomplete
# or
yarn add use-places-autocomplete
```

Inside the component, we initialize it like this:

```tsx
import usePlacesAutocomplete, { getGeocode, getLatLng } from "use-places-autocomplete";

const {
  ready,          // boolean: is the Google API ready
  value,          // string: current input value
  suggestions,    // { status, data } object for autocomplete suggestions
  setValue,       // function to update input value
  clearSuggestions // function to clear suggestions list
} = usePlacesAutocomplete({
  debounce: 300,  // debounce delay for API calls
});
```

- `ready` indicates if the Google Places API is loaded and ready to use.  
- `value` and `setValue` are used to control the input text.  
- `suggestions` contains the status and array of suggested place predictions.  
- `clearSuggestions` clears the suggestion list (usually called once a selection is made).

This hook simplifies most of the heavy lifting involved in managing autocomplete requests and results.

---

## Managing Controlled Input State

React recommends controlled components for form inputs to keep UI state predictable.

In our `PlacesAutocomplete` component, the text input’s value is tied to the hook’s `value` state:

```tsx
<input
  type="text"
  value={value}
  onChange={(e) => {
    setValue(e.target.value);
  }}
  disabled={!ready}
  placeholder="Search a location"
/>
```

- When the user types, `onChange` updates the hook’s internal value via `setValue`.  
- The `disabled` prop disables the input until the Google Places API is ready.  
- The input’s `value` is controlled by the hook, ensuring sync between UI and hook state.

This controlled pattern is essential for predictability, especially when suggestions depend on the input.

---

## Rendering Suggestions and Handling Selection

The `suggestions` object from the hook has the following shape:

```ts
{
  status: "OK" | "ZERO_RESULTS" | ...,
  data: Array<Prediction>
}
```

Each `Prediction` object contains detailed information about a suggested place.

We typically want to display a dropdown list of suggestions as the user types:

```tsx
{suggestions.status === "OK" && (
  <ul>
    {suggestions.data.map(({ place_id, description }) => (
      <li key={place_id} onClick={() => handleSelect(description)}>
        {description}
      </li>
    ))}
  </ul>
)}
```

The `handleSelect` function is triggered when the user clicks a suggestion. It should:

1. Update the input value to the selected suggestion  
2. Clear suggestions  
3. Optionally, retrieve detailed info (e.g., lat/lng) using `getGeocode` and `getLatLng` helpers from `use-places-autocomplete`  

Example:

```tsx
const handleSelect = async (address: string) => {
  setValue(address, false); // update input but do not fetch suggestions
  clearSuggestions();

  try {
    const results = await getGeocode({ address });
    const { lat, lng } = await getLatLng(results[0]);
    // Pass lat/lng and address to parent or state
    onSelect({ address, lat, lng });
  } catch (error) {
    console.error("Error getting geocode:", error);
  }
};
```

This approach encapsulates the logic for fetching place details and communicating the final selection to the parent component.

---

## Accessibility Considerations with `useId`

Accessible autocomplete inputs improve the experience for keyboard and screen reader users.

React’s `useId` hook (React 18+) helps generate unique IDs to link the input and the list of suggestions:

```tsx
import { useId } from "react";

const inputId = useId();
const listboxId = `${inputId}-listbox`;
```

In the input element:

```tsx
<input
  id={inputId}
  aria-autocomplete="list"
  aria-controls={listboxId}
  aria-expanded={suggestions.status === "OK"}
  aria-activedescendant={activeId} // dynamically set when navigating suggestions
  ...
/>
```

In the suggestions list:

```tsx
<ul id={listboxId} role="listbox">
  {suggestions.data.map(({ place_id, description }, index) => {
    const optionId = `${listboxId}-option-${index}`;
    return (
      <li
        key={place_id}
        id={optionId}
        role="option"
        aria-selected={activeIndex === index}
        onClick={() => handleSelect(description)}
      >
        {description}
      </li>
    );
  })}
</ul>
```

This markup:

- Connects the input and suggestion list via ARIA attributes  
- Ensures screen readers announce the suggestions properly  
- Supports keyboard navigation when implemented (e.g., arrow keys)

While keyboard navigation is beyond the scope of this chapter, adding `aria-activedescendant` prepares the component for it.

---

## Callback Props for Parent Communication

To keep the component reusable and decoupled, we expose callback props to notify the parent about meaningful events, such as:

- `onSelect`: when the user picks a place (address + lat/lng)  
- `onChange`: when the input value changes (optional, for controlled usage)  
- `onClear`: when suggestions are cleared (optional)

Example prop definitions in TypeScript:

```ts
interface PlacesAutocompleteProps {
  onSelect: (selection: { address: string; lat: number; lng: number }) => void;
  onChange?: (value: string) => void;
  placeholder?: string;
}
```

Usage inside the component:

```tsx
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setValue(e.target.value);
  if (onChange) onChange(e.target.value);
};
```

This pattern allows parent components to respond to user input or selection and integrate the autocomplete into different workflows (e.g., forms, map centers, etc.).

---

## Putting It All Together: Complete Component Example

Here is a complete example of the `PlacesAutocomplete` component implementing the concepts discussed:

```tsx
"use client";

import React, { useState } from "react";
import usePlacesAutocomplete, { getGeocode, getLatLng } from "use-places-autocomplete";
import { useId } from "react";

interface PlacesAutocompleteProps {
  onSelect: (selection: { address: string; lat: number; lng: number }) => void;
  onChange?: (value: string) => void;
  placeholder?: string;
}

export const PlacesAutocomplete: React.FC<PlacesAutocompleteProps> = ({
  onSelect,
  onChange,
  placeholder = "Search a location",
}) => {
  const {
    ready,
    value,
    suggestions: { status, data },
    setValue,
    clearSuggestions,
  } = usePlacesAutocomplete({
    debounce: 300,
  });

  const inputId = useId();
  const listboxId = `${inputId}-listbox`;

  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
    if (onChange) {
      onChange(e.target.value);
    }
  };

  const handleSelect = async (address: string) => {
    setValue(address, false);
    clearSuggestions();

    try {
      const results = await getGeocode({ address });
      const { lat, lng } = await getLatLng(results[0]);
      onSelect({ address, lat, lng });
    } catch (error) {
      console.error("Error fetching geocode:", error);
    }
  };

  return (
    <div style={{ position: "relative" }}>
      <input
        id={inputId}
        type="text"
        value={value}
        onChange={handleInputChange}
        disabled={!ready}
        placeholder={placeholder}
        aria-autocomplete="list"
        aria-controls={listboxId}
        aria-expanded={status === "OK"}
        aria-activedescendant={
          activeIndex !== null ? `${listboxId}-option-${activeIndex}` : undefined
        }
        autoComplete="off"
        style={{ width: "100%" }}
      />

      {status === "OK" && data.length > 0 && (
        <ul
          id={listboxId}
          role="listbox"
          style={{
            position: "absolute",
            zIndex: 1000,
            background: "white",
            margin: 0,
            padding: 0,
            listStyle: "none",
            width: "100%",
            maxHeight: "200px",
            overflowY: "auto",
            border: "1px solid #ccc",
          }}
        >
          {data.map(({ place_id, description }, index) => {
            const optionId = `${listboxId}-option-${index}`;
            return (
              <li
                key={place_id}
                id={optionId}
                role="option"
                aria-selected={activeIndex === index}
                onClick={() => handleSelect(description)}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
                style={{
                  padding: "0.5rem",
                  cursor: "pointer",
                  backgroundColor: activeIndex === index ? "#bde4ff" : "transparent",
                }}
              >
                {description}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
```

---

## Conclusion

In this chapter, we created a robust and reusable `PlacesAutocomplete` React component using the `use-places-autocomplete` hook. We covered:

- How to integrate with Google Places API via the hook  
- Managing controlled input state for predictability  
- Rendering and selecting autocomplete suggestions  
- Implementing accessibility best practices using `useId` and ARIA attributes  
- Designing the component with callback props for flexible parent communication  

This component forms a critical UI piece in Next.js apps that require location inputs and can be further enhanced with keyboard navigation, custom styling, and error handling. With this foundation, you can confidently integrate powerful location search functionality into your projects.

---

**Next up:** In the following chapters, we will explore integrating this autocomplete component with map displays and handling user-selected locations across the app state.