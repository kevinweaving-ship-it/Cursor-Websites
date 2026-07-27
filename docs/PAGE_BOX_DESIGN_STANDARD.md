# Page box design standard (intro box duplicated for rest of page)

**Reference:** The “Class results, regattas and sailors for this fleet.” intro box at the top of the class page.

## What’s done in the intro box

| Property | Value | Duplicated to |
|----------|--------|----------------|
| **Border** | `2px solid #001f3f` | All `.card` (title, stats, REGATTAS, Clubs, Sailors) |
| **Border radius** | `8px` | All `.card` |
| **Background** | `#fff` | All `.card` |
| **Box shadow** | `0 1px 3px rgba(0,31,63,0.08)` | All `.card` and `.home-intro-box` |
| **Body text** | `0.9rem`, `#334155`, line-height 1.5 | `.card .table td`, `.class-stats a.stats-link` (font-size) |
| **Headings / links** | `#001f3f`, font-weight 600/700 | `.card .section-title`, `.table thead th`, `.card .table a` |
| **Font** | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif` | Body (all page) |

## CSS variables (main.css)

- `--box-border`: 2px solid #001f3f  
- `--box-radius`: 8px  
- `--box-shadow`: 0 1px 3px rgba(0,31,63,0.08)  
- `--box-body-text`: #334155  
- `--box-body-size`: 0.9rem  
- `--box-heading-color`: #001f3f  

Cards and intro box use these so the whole class page (and sailor/regatta/master layout pages) share the same look.
