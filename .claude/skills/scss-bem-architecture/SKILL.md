---
name: scss-bem-architecture
description: This skill should be used when writing CSS or SCSS for Vue components, naming CSS classes, using CSS custom properties, structuring scoped styles, writing responsive media queries, or deciding how to handle theming and shared style values.
version: 1.0.0
---

# SCSS Architecture and BEM Naming

## Component Styles Setup

Always use `<style scoped lang="scss">` in Vue components:

```vue
<style scoped lang="scss">
.component-name {
  // styles here
}
</style>
```

## BEM Naming Convention

Use Block__Element--Modifier pattern:

```scss
// Block
.project-card { }

// Element (part of the block)
.project-card__title { }
.project-card__thumbnail { }
.project-card__actions { }

// Modifier (variation of block or element)
.project-card--featured { }
.project-card__title--truncated { }
```

```vue
<template>
  <div class="project-card project-card--featured">
    <h2 class="project-card__title">{{ title }}</h2>
    <div class="project-card__actions">
      <button class="project-card__btn">Edit</button>
    </div>
  </div>
</template>
```

## CSS Custom Properties for Theming

Define theme tokens as CSS custom properties, use them throughout:

```scss
// Global (in main.scss or :root)
:root {
  --color-primary: rgb(79, 70, 229);
  --color-surface: rgb(30, 30, 46);
  --color-text: rgb(205, 214, 244);
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --border-radius: 8px;
}

// Component usage
.project-card {
  background: var(--color-surface);
  color: var(--color-text);
  padding: var(--spacing-md);
  border-radius: var(--border-radius);
}
```

## Responsive Design: Mobile-First

Start with mobile styles, add breakpoints for larger screens:

```scss
.project-grid {
  display: grid;
  grid-template-columns: 1fr;          // mobile: single column
  gap: var(--spacing-md);

  @media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);  // tablet: 2 columns
  }

  @media (min-width: 1200px) {
    grid-template-columns: repeat(3, 1fr);  // desktop: 3 columns
  }
}
```

## Rules

- **No inline styles** in templates — always use scoped SCSS classes
- **No `:deep()` selectors** — prefer props or slots for child component customization
- **No hardcoded colors** — use CSS custom properties
- **Avoid `!important`** — fix specificity instead
- **Keep nesting shallow** — max 3 levels deep in SCSS
