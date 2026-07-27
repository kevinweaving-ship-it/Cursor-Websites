# Regatta Results HTML Viewer

## Overview
The HTML viewer (`Regatta results managementV19.html`) displays sailing regatta results in a Sailwave-style format with inline editing capabilities.

## File Structure
- **Main File**: `Regatta results managementV19.html`
- **API Backend**: `api.py` (FastAPI server on port 8082)
- **Database**: PostgreSQL (`master` database)

## Key Features

### 1. Fleet Display
- **Header Information**: Shows fleet name, races sailed, discards, entries count
- **Results Table**: Displays all sailors with ranks, names, scores, totals
- **Two-Line Format**: Names and race scores split across two lines for better readability

### 2. Inline Editing
- **Sailor Names**: Click to edit with live SAS ID search
- **Race Scores**: Direct editing of individual race results
- **Club Codes**: Auto-complete from database
- **Real-time Updates**: Changes saved immediately via API

### 3. SAS ID Matching
- **Auto-suggestions**: Dropdown with matching sailors
- **Exact Match Priority**: SAS IDs assigned only on exact name matches
- **Temp ID Creation**: New temporary IDs for unmatched sailors
- **Visual Feedback**: Red highlighting for name mismatches

## Data Flow

### 1. Page Load
```javascript
// Load regatta list
const all = await fetch(`${API}/api/regattas`).json();

// Load specific regatta data
const rows = await fetch(`${API}/api/regatta/${regatta_id}`).json();
```

### 2. Data Rendering
```javascript
// Group data by fleet blocks
const by = {};
rows.forEach(r => (by[r.block_id] ||= []).push(r));

// Render each fleet
Object.entries(by).map(([bid, items]) => {
    const h = items[0]; // Fleet header data
    // Build HTML table with sailor results
});
```

### 3. Fleet Header Construction
```javascript
// Fleet name
const fleetName = h.block_fleet_label || h.fleet_label || 'Fleet';

// Sailed line
const sailed = h.races_sailed ?? '';
const discards = h.discard_count ?? 0;
const tocount = h.to_count ?? Math.max(0, (h.races_sailed||0)-(h.discard_count||0));
const entries = h.entries_count ?? items.length;

// Display
sailingParams.textContent = 
    `Sailed: ${sailed}, Discards: ${discards}, To count: ${tocount}, ` +
    `Entries: ${entries}, Scoring system: ${h.scoring_system || 'Appendix A'}`;
```

## API Integration

### Endpoints Used
- `GET /api/regattas` - List all regattas
- `GET /api/regatta/{id}` - Get regatta data via `vw_regatta_page` view
- `GET /api/people/search` - Search sailors by name
- `POST /api/people/temp` - Create temporary sailor
- `PATCH /api/result/{result_id}` - Update result fields

### Data Structure
The API returns data from `vw_regatta_page` view with:
- Fleet header fields: `block_fleet_label`, `races_sailed`, `discard_count`, `to_count`, `entries_count`
- Sailor fields: `result_id`, `rank`, `helm_name`, `crew_name`, `sail_number`, `club_code`
- Race scores: `R1`, `R2`, `R3`... extracted from `race_scores` JSONB
- Totals: `total_points_raw`, `nett_points_raw`

## CSS Styling

### Two-Line Format
```css
/* Names: first name on top, surname below */
td.name .first, td.name .last {
    display: block;
    line-height: 1.15;
}

/* Race scores: number on top, penalty code below */
td.score .num, td.score .code {
    display: block;
    line-height: 1.15;
}

td.score .code {
    font-size: .85em;
    color: #ff6b6b;
}
```

### Table Layout
```css
table {
    table-layout: fixed;
    width: 100%;
}

td.name {
    max-width: 90px;
    overflow-wrap: anywhere;
}

td.score {
    max-width: 54px;
}
```

## JavaScript Functions

### Name Formatting
```javascript
function fmtNameTwoLines(fullName) {
    if(!fullName) return '';
    const parts = fullName.trim().split(/\s+/);
    if(parts.length === 1) return `<span class="first">${parts[0]}</span>`;
    const last = parts.pop();
    const first = parts.join(' ');
    return `<span class="first">${first}</span><span class="last">${last}</span>`;
}
```

### Score Formatting
```javascript
function fmtScoreTwoLines(s) {
    if(!s) return '';
    const penalty = /\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i;
    const stripped = s.replace(/^\(/,'').replace(/\)$/,'');
    
    if(penalty.test(stripped)) {
        const parts = stripped.split(/\s+/);
        const num = parts.shift() || stripped;
        const code = parts.join(' ') || stripped.match(penalty)?.[0] || '';
        return `<span class="num">${num}</span><span class="code">${code}</span>`;
    }
    
    if(s.startsWith('(') && s.endsWith(')')) {
        const inner = s.slice(1,-1);
        return `(<span class="num">${inner}</span>)`;
    }
    
    return `<span class="num">${s}</span>`;
}
```

### Inline Editing
```javascript
// Make person field editable with live search
function makePersonEditable(td, type, resultId) {
    td.onclick = function() {
        // Create input field
        const input = document.createElement('input');
        input.value = td.textContent.trim();
        
        // Attach live search
        attachLiveSearch(input, type, resultId, td);
        
        // Replace cell content
        td.innerHTML = '';
        td.appendChild(input);
        input.focus();
    };
}
```

### Live Search Dropdown
```javascript
function attachLiveSearch(input, type, resultId, td) {
    let dropdown = null;
    
    input.oninput = debounce(async (e) => {
        const query = e.target.value.trim();
        if(query.length < 2) {
            if(dropdown) dropdown.remove();
            return;
        }
        
        // Search API
        const results = await fetch(`${API}/api/people/search?name=${encodeURIComponent(query)}`).json();
        
        // Create dropdown
        if(dropdown) dropdown.remove();
        dropdown = createDropdown(results, input, type, resultId, td);
    }, 300);
}
```

## Data Validation

### Client-Side Checks
- Name length validation
- Race score format validation
- Club code existence check
- SAS ID format validation

### Server-Side Validation
- Database constraint checks
- SAS ID existence verification
- Club code mapping validation
- Race score calculation verification

## Error Handling

### API Errors
```javascript
try {
    const response = await fetch(url);
    if(!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
} catch(error) {
    console.error('API Error:', error);
    // Show user-friendly error message
}
```

### Database Errors
- Constraint violations logged
- Rollback on failed transactions
- User notification of validation failures

## Performance Optimizations

### Caching
- Regatta list cached on load
- Sailor search results cached
- Debounced search input (300ms delay)

### Rendering
- Virtual scrolling for large fleets
- Lazy loading of race score details
- Efficient DOM updates

## Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ features used
- CSS Grid and Flexbox support required
- Fetch API required (polyfill for older browsers)

## Security Considerations
- Input sanitization for XSS prevention
- SQL injection protection via parameterized queries
- CSRF protection on state-changing operations
- Rate limiting on search endpoints
