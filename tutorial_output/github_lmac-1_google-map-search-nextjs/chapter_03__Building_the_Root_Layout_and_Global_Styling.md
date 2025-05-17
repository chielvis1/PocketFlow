# Chapter 3: **Building the Root Layout and Global Styling**  

# Chapter 3: Building the Root Layout and Global Styling

In this chapter, we will implement the `RootLayout` component (`app/layout.tsx`), which serves as the foundational layout for our Next.js 13 application. We will explore how layouts work in Next.js 13, how to set important metadata for SEO and Progressive Web App (PWA) support, and how to manage global CSS and font imports. Additionally, we’ll discuss accessibility best practices and introduce global theming to ensure a consistent user experience across the app.

---

## Table of Contents

- [3.1 Introduction to Layouts in Next.js 13](#31-introduction-to-layouts-in-nextjs-13)  
- [3.2 Creating the RootLayout Component](#32-creating-the-rootlayout-component)  
- [3.3 Managing Metadata for SEO and PWA](#33-managing-metadata-for-seo-and-pwa)  
- [3.4 Importing Global CSS and Fonts](#34-importing-global-css-and-fonts)  
- [3.5 Accessibility Considerations](#35-accessibility-considerations)  
- [3.6 Implementing Global Theming](#36-implementing-global-theming)  
- [3.7 Conclusion](#37-conclusion)  

---

## 3.1 Introduction to Layouts in Next.js 13

Next.js 13 introduces a powerful new `app/` directory structure and a special concept called **layouts**. Unlike traditional pages, layouts are React Server Components that wrap around your pages and other nested layouts, defining a shared UI structure.

### Why use Layouts?

- **Consistent UI**: Layouts allow you to define headers, footers, navigation, or any other persistent UI elements once, and share them across many pages.
- **Performance**: Because layouts are React Server Components, they can fetch data on the server and send fully rendered HTML to the client.
- **Nested Layouts**: You can create layouts at different folder levels, enabling scoped UI and data management.

The `RootLayout` is special because it wraps your entire app, setting the stage for all pages and nested layouts.

---

## 3.2 Creating the RootLayout Component

The root layout lives at `app/layout.tsx`. Here’s a simple example illustrating its structure:

```tsx
// app/layout.tsx
import './globals.css';
import { Inter } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata = {
  title: 'My Next.js App',
  description: 'An app integrating Google Maps and Places Autocomplete',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <head />
      <body>
        {/* Global header can go here */}
        {children}
        {/* Global footer can go here */}
      </body>
    </html>
  );
}
```

### Explanation

- **HTML Structure**: The root layout returns the entire HTML skeleton (`<html>`, `<body>`) required for your app.
- **Font Integration**: We use Next.js’s built-in Google Fonts optimization to load the Inter font and apply it globally using a CSS variable.
- **Metadata**: `metadata` is an exported object Next.js uses to inject SEO-relevant meta tags.
- **`children` Prop**: Represents the nested pages or layouts rendered inside this root layout.

---

## 3.3 Managing Metadata for SEO and PWA

SEO and PWA metadata improve your app’s discoverability and functionality on mobile devices.

### Defining Metadata in Next.js 13

You can export a `metadata` object from your layout or page files containing relevant meta information:

```tsx
export const metadata = {
  title: 'My Next.js App',
  description: 'An app integrating Google Maps and Places Autocomplete',
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/site.webmanifest',
  themeColor: '#317EFB',
  openGraph: {
    title: 'My Next.js App',
    description: 'Google Maps and Places autocomplete integration',
    url: 'https://myapp.example.com',
    siteName: 'Next.js Maps',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Next.js Maps',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
};
```

### What this does:

- **Title and Description**: Shown on search results.
- **Icons and Manifest**: Enables PWA features like "Add to Home Screen."
- **OpenGraph Tags**: Improve link previews on social media.
- **Theme Color**: Sets the browser toolbar color on mobile.

Next.js automatically injects this metadata into the `<head>` of your document.

---

## 3.4 Importing Global CSS and Fonts

In Next.js 13’s `app/` directory, global CSS must be imported at the root layout level (`app/layout.tsx`):

```tsx
import './globals.css';
```

### Why here?

- CSS imported here applies globally, affecting all nested layouts and pages.
- You cannot import global CSS inside components or pages anymore.

### Example: globals.css

```css
/* globals.css */
html, body {
  margin: 0;
  padding: 0;
  font-family: var(--font-inter), sans-serif;
  background-color: #f7f8fa;
  color: #333;
}

a {
  color: #317efb;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
```

### Font Setup

Using Next.js’s built-in Google Fonts integration (via `next/font/google`) helps:

- Optimize font loading.
- Avoid layout shifts.
- Use CSS variables to apply fonts globally.

See the font import example in the `RootLayout` above.

---

## 3.5 Accessibility Considerations

Accessibility (a11y) is essential for building inclusive web apps. When designing your `RootLayout`, consider:

- **Language attribute**: Set `lang="en"` on the `<html>` tag to help screen readers.
- **Skip links**: Provide a "skip to content" link for keyboard users.
- **Focus management**: Ensure focus styles are visible and logical.
- **Contrast and font sizes**: Use accessible color contrasts and readable fonts.

Example of a skip link in the layout:

```tsx
<body>
  <a href="#main-content" className="skip-link">Skip to main content</a>
  {children}
</body>
```

And CSS for `.skip-link`:

```css
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #000;
  color: #fff;
  padding: 8px;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

---

## 3.6 Implementing Global Theming

In an app integrating Google Maps and autocomplete, consistent theming is crucial.

### Using CSS Variables

Define color palettes and spacing in `globals.css`:

```css
:root {
  --color-primary: #317efb;
  --color-secondary: #f5f7fa;
  --color-text: #333333;
  --spacing-unit: 8px;
}
```

Use them throughout your app:

```css
body {
  background-color: var(--color-secondary);
  color: var(--color-text);
  font-family: var(--font-inter), sans-serif;
}
```

### Using React Context (Optional)

For dynamic theming (e.g., light/dark mode), you can create a React Context provider at the root layout level and pass theme state down.

Example snippet:

```tsx
'use client';

import { createContext, useState } from 'react';

export const ThemeContext = createContext({ theme: 'light', toggleTheme: () => {} });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState('light');

  function toggleTheme() {
    setTheme(theme === 'light' ? 'dark' : 'light');
  }

  return (
    <html lang="en" data-theme={theme}>
      <body>
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
          {children}
        </ThemeContext.Provider>
      </body>
    </html>
  );
}
```

And CSS can use `[data-theme="dark"]` selectors to apply dark mode styles.

---

## 3.7 Conclusion

In this chapter, we built the `RootLayout` component, the foundation of our Next.js 13 app. We learned about:

- The new layout system and React Server Components
- How to manage SEO and PWA metadata declaratively
- Importing global CSS and fonts the Next.js 13 way
- Accessibility best practices to make the app usable by all
- Approaches to global theming for consistent styling

With a solid root layout in place, you are now ready to build nested layouts and pages that inherit this shared structure and styling, keeping your app maintainable, performant, and user-friendly.

---

**Next up:** Chapter 4 will dive into creating the main search page, integrating Google Maps and Places Autocomplete components with interactive UI and state management.