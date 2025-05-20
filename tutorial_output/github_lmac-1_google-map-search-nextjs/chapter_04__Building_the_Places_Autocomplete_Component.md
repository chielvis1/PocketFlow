# Chapter 4: **Building the Places Autocomplete Component**  

# Chapter 4: Building the Places Autocomplete Component

In this chapter, we will build the `PlacesAutocomplete` component—a core UI piece that leverages the Google Places API to provide location suggestions as users type. Using the popular `use-places-autocomplete` hook, we'll manage user input, display suggestions dynamically, handle selection events, and address important accessibility concerns to ensure a smooth and inclusive user experience.

---

## 4.1 Introduction to `PlacesAutocomplete`

The `PlacesAutocomplete` component acts as an input field with an autocomplete dropdown, powered by Google Places API. As a user types, it fetches suggested places matching the input, and lets users select a suggestion to update the UI or trigger further actions.

At its core, this component:

- Integrates with the Google Places API via the `use-places-autocomplete` React hook.
- Manages input state and suggestion lifecycle.
- Exposes callback props to notify parent components of selection.
- Implements accessibility best practices for keyboard navigation and screen readers.

---

## 4.2 Setting Up the `use-places-autocomplete` Hook

The `use-places-autocomplete` hook abstracts the complexity of dealing with Google Places API requests and response handling. It internally manages the autocomplete service, fetching suggestions as input changes.

### Installation

If not already added, install the hook:

```bash
npm install use-places-autocomplete
```

or

```bash
yarn add use-places-autocomplete
```

### Basic Usage

```tsx
import usePlacesAutocomplete from "use-places-autocomplete";

function Component() {
  const {
    ready,      // Boolean indicating if the Google Places API is loaded
    value,      // Current input value
    suggestions, // Suggestions object: { status, data }
    setValue,   // Function to update input value
    clearSuggestions, // Clears the suggestions list
  } = usePlacesAutocomplete();

  // ...
}
```

---

## 4.3 Creating the `PlacesAutocomplete` Component

Let's build the component step-by-step.

### 4.3.1 Component Props

To make it reusable and flexible, our component will accept:

- `onSelect`: A callback invoked when a user selects a place suggestion.
- `placeholder`: Optional placeholder text for the input.
- `defaultValue`: Optional initial value of the input.

```tsx
interface PlacesAutocompleteProps {
  onSelect: (address: string, placeId?: string) => void;
  placeholder?: string;
  defaultValue?: string;
}
```

### 4.3.2 Managing Input and Suggestions

We'll use the `use-places-autocomplete` hook to manage input and suggestions.

```tsx
import React, { useId } from "react";
import usePlacesAutocomplete, { Suggestion } from "use-places-autocomplete";

export const PlacesAutocomplete: React.FC<PlacesAutocompleteProps> = ({
  onSelect,
  placeholder = "Search places...",
  defaultValue = "",
}) => {
  const id = useId();

  const {
    ready,
    value,
    suggestions: { status, data },
    setValue,
    clearSuggestions,
  } = usePlacesAutocomplete({
    requestOptions: {
      /* Optional: location biasing, radius, types, etc. */
    },
    debounce: 300,
  });

  // Handle user typing
  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  // Handle selection of a suggestion
  const handleSelect = (suggestion: Suggestion) => {
    setValue(suggestion.description, false);
    clearSuggestions();
    onSelect(suggestion.description, suggestion.place_id);
  };

  // ...

  return (
    <div>
      {/* Input and suggestions UI */}
    </div>
  );
};
```

> **Note:** We use `useId` to generate unique ids for accessibility attributes.

---

## 4.4 Displaying Suggestions

### 4.4.1 Rendering the Suggestions List

When status is `"OK"`, the `data` array contains place suggestions. Each suggestion includes:

- `description`: The readable address or place name.
- `place_id`: Unique Google Places identifier.

We will render these as a list below the input.

```tsx
<ul role="listbox" id={`${id}-listbox`} className="suggestions-list">
  {status === "OK" &&
    data.map(({ place_id, description }) => (
      <li
        key={place_id}
        role="option"
        id={`${id}-option-${place_id}`}
        tabIndex={-1}
        onClick={() => handleSelect({ place_id, description })}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleSelect({ place_id, description });
          }
        }}
        className="suggestion-item"
      >
        {description}
      </li>
    ))}
</ul>
```

### 4.4.2 Styling Suggestions

You can style the suggestions list and items using CSS or Tailwind (depending on your stack) to highlight hovered/focused items and provide clear visual feedback.

---

## 4.5 Handling Keyboard Navigation and Accessibility

Accessibility is critical for autocomplete components.

### 4.5.1 ARIA Roles and Attributes

- The input should have `aria-autocomplete="list"` and `aria-controls` referencing the listbox.
- The suggestion list should have `role="listbox"`.
- Each suggestion should have `role="option"` and a unique `id`.
- The input should have `aria-activedescendant` set to the currently highlighted suggestion's id.

### 4.5.2 Managing Focus and Keyboard

Implement keyboard navigation:

- **Arrow Down / Up:** Moves focus through suggestions.
- **Enter / Space:** Selects the focused suggestion.
- **Escape:** Closes the suggestions.

You can manage a `highlightedIndex` state to track which suggestion is focused.

Example snippet:

```tsx
const [highlightedIndex, setHighlightedIndex] = React.useState(-1);

const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
  switch (e.key) {
    case "ArrowDown":
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev < data.length - 1 ? prev + 1 : 0
      );
      break;
    case "ArrowUp":
      e.preventDefault();
      setHighlightedIndex((prev) =>
        prev > 0 ? prev - 1 : data.length - 1
      );
      break;
    case "Enter":
      e.preventDefault();
      if (highlightedIndex >= 0) {
        handleSelect(data[highlightedIndex]);
      }
      break;
    case "Escape":
      clearSuggestions();
      break;
  }
};
```

Apply `aria-activedescendant` on the input:

```tsx
<input
  type="text"
  value={value}
  onChange={handleInput}
  onKeyDown={handleKeyDown}
  aria-autocomplete="list"
  aria-controls={`${id}-listbox`}
  aria-activedescendant={
    highlightedIndex >= 0
      ? `${id}-option-${data[highlightedIndex].place_id}`
      : undefined
  }
  placeholder={placeholder}
  disabled={!ready}
/>
```

---

## 4.6 Full Component Example

Putting it all together:

```tsx
import React, { useState, useId } from "react";
import usePlacesAutocomplete, { Suggestion } from "use-places-autocomplete";

interface PlacesAutocompleteProps {
  onSelect: (address: string, placeId?: string) => void;
  placeholder?: string;
  defaultValue?: string;
}

export const PlacesAutocomplete: React.FC<PlacesAutocompleteProps> = ({
  onSelect,
  placeholder = "Search places...",
  defaultValue = "",
}) => {
  const id = useId();
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const {
    ready,
    value,
    suggestions: { status, data },
    setValue,
    clearSuggestions,
  } = usePlacesAutocomplete({
    debounce: 300,
    defaultValue,
  });

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  const handleSelect = (suggestion: Suggestion) => {
    setValue(suggestion.description, false);
    clearSuggestions();
    setHighlightedIndex(-1);
    onSelect(suggestion.description, suggestion.place_id);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (status !== "OK") return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev < data.length - 1 ? prev + 1 : 0));
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : data.length - 1));
        break;
      case "Enter":
        e.preventDefault();
        if (highlightedIndex >= 0) {
          handleSelect(data[highlightedIndex]);
        }
        break;
      case "Escape":
        clearSuggestions();
        setHighlightedIndex(-1);
        break;
    }
  };

  return (
    <div className="places-autocomplete">
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        aria-autocomplete="list"
        aria-controls={`${id}-listbox`}
        aria-activedescendant={
          highlightedIndex >= 0 ? `${id}-option-${data[highlightedIndex].place_id}` : undefined
        }
        disabled={!ready}
        role="combobox"
        aria-expanded={status === "OK"}
        aria-haspopup="listbox"
        aria-owns={`${id}-listbox`}
        autoComplete="off"
        spellCheck={false}
      />

      {status === "OK" && (
        <ul role="listbox" id={`${id}-listbox`} className="suggestions-list">
          {data.map(({ place_id, description }, index) => (
            <li
              key={place_id}
              id={`${id}-option-${place_id}`}
              role="option"
              tabIndex={-1}
              className={`suggestion-item ${highlightedIndex === index ? "highlighted" : ""}`}
              onClick={() => handleSelect({ place_id, description })}
              onMouseEnter={() => setHighlightedIndex(index)}
              onMouseLeave={() => setHighlightedIndex(-1)}
            >
              {description}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
```

---

## 4.7 Accessibility Summary

- The input uses `role="combobox"` with appropriate ARIA attributes.
- The listbox and options use `role="listbox"` and `role="option"`.
- Keyboard navigation is supported for arrow keys, enter, and escape.
- Visual focus and hover states are synchronized with keyboard navigation.

---

## 4.8 Conclusion

In this chapter, we successfully created the `PlacesAutocomplete` component. By integrating the `use-places-autocomplete` hook, we abstracted Google Places API complexities and focused on building a user-friendly autocomplete experience.

We managed input state, dynamically rendered suggestions, handled selection events with callback props, and ensured accessibility through ARIA roles and keyboard navigation.

This component provides a solid foundation for location input in your Next.js + Google Maps API application, promoting reusability and a polished UX.

In the next chapter, we will explore how to integrate this component within a larger form and process selected place data to display on the map.