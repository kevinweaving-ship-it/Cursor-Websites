# Layout Plan: Search Header Container
## Mobile-First Design

## Current Structure
```
<header class="site-header">  <!-- Dark blue header with logo/auth -->
  Logo | Auth | Menu
</header>

<main>
  <div class="search-row-container">  <!-- Currently plain white background -->
    <div class="search-row">
      Sailor Search | Regatta Search
    </div>
  </div>
</main>
```

## Proposed Structure

### Option 1: Separate Search Header Container (Recommended)
```
<header class="site-header">  <!-- Existing header -->
  Logo | Auth | Menu
</header>

<main>
  <div class="search-header-container">  <!-- NEW: Dark blue container -->
    <div class="container">
      <div class="search-row">
        Sailor Search | Regatta Search
      </div>
    </div>
  </div>
  
  <div class="search-results-container">  <!-- Results below header -->
    <div id="sailor-search-results"></div>
  </div>
</main>
```

## Design Specifications

### Search Header Container
- **Background**: Dark blue (#001f3f) - matching site-header
- **Width**: Full width (100%) - fits mobile view, responsive
- **Border radius**: 12px (mobile), 16px (desktop)
- **Padding**: 
  - Mobile: 12px top/bottom, 16px left/right
  - Desktop: 16px top/bottom, 20px left/right
- **Margin-top**: 12px (small gap from site-header)
- **Margin-bottom**: 0 (results container handles spacing)
- **Box shadow**: Subtle shadow for depth (optional)

### Search Forms Inside Container
- **Text color**: White (#ffffff) for labels
- **Input background**: White or light gray
- **Input text**: Dark (#001f3f)
- **Border radius**: 8px for inputs
- **Gap between searches**: 
  - Mobile: 0.75rem
  - Desktop: 1.5rem

### Mobile-First Responsive
- **Mobile (< 768px)**:
  - Stack vertically if needed OR keep horizontal with smaller gaps
  - Smaller padding
  - Smaller font sizes
  - Touch-friendly input sizes (min 44px height)
  
- **Desktop (≥ 768px)**:
  - Horizontal layout
  - Larger padding
  - More spacing

## CSS Classes Needed

```css
.search-header-container {
  background: #001f3f;
  border-radius: 12px;
  margin-top: 12px;
  padding: 12px 16px;
  /* Mobile-first */
}

@media (min-width: 768px) {
  .search-header-container {
    border-radius: 16px;
    margin-top: 16px;
    padding: 16px 20px;
  }
}

.search-header-container .search-row {
  /* Adjust existing search-row styles for white text */
}

.search-header-container .sailor-search-label,
.search-header-container .regatta-search-label {
  color: #ffffff;
}

.search-header-container .sailor-search-input,
.search-header-container .regatta-search-input {
  background: #ffffff;
  color: #001f3f;
}
```

## Decisions Made ✅

1. **Search results location**: ✅ **Results BELOW** the search header/bar (cleaner separation)
2. **Container width**: To be decided - Full width or constrained?
3. **Mobile layout**: To be decided - Side-by-side or stacked?
4. **Border/shadow**: To be decided - Add subtle styling?

## Structure Confirmed

```
<header class="site-header">  <!-- Dark blue header with logo/auth -->
  Logo | Auth | Menu
</header>

<main>
  <div class="search-header-container">  <!-- NEW: Dark blue search bar -->
    <div class="container">
      <div class="search-row">
        Sailor Search | Regatta Search
      </div>
    </div>
  </div>
  
  <!-- Results appear BELOW search header -->
  <div class="search-results-container">
    <div id="sailor-search-results"></div>
    <div id="public-regattas-list"></div>
  </div>
</main>
```

## Implementation Order

1. Create `.search-header-container` wrapper
2. Move `.search-row` inside new container
3. Add dark blue background and rounded corners
4. Adjust text colors (white labels, white text)
5. Add mobile-first responsive styles
6. Test on mobile devices
7. Adjust spacing/padding as needed
