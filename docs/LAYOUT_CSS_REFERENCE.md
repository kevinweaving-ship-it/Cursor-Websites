# Layout CSS reference — default for all pages (https://sailingsa.co.za/)

This is the full contents of **`sailingsa/frontend/css/main.css`**, the default stylesheet for the site. It applies to the root document and all pages (landing, class, regatta, sailor, club, etc.).

**Source file:** `sailingsa/frontend/css/main.css`

---

```css
/* SailingSA Main Stylesheet */

:root {
    --primary-color: #6B2C91;
    --secondary-color: #DC143C;
    --text-color: #1e293b;
    --bg-color: #f5f7fa;
    --white: #ffffff;
    --border-color: #ddd;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    overflow-x: hidden;
    overflow-y: scroll;
    scroll-behavior: smooth;
}
body {
    overflow-x: hidden;
    overflow-y: visible;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #f5f7fa;
    color: #1e293b;
    line-height: 1.6;
}

main {
    background: transparent;
}

.container {
    max-width: 1100px;
    margin: auto;
    padding: 12px;
}

/* Table horizontal scroll on mobile */
.table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

/* Hide less important columns on small screens */
@media (max-width: 600px) {
    .hide-mobile {
        display: none !important;
    }
}

/* Cards: match landing page; white, no dark backgrounds */
.card {
    background: #ffffff;
    border-radius: 10px;
    padding: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 16px;
}

/* Minimum touch target for buttons */
button,
.btn,
[role="button"] {
    min-height: 44px;
}

/* Sortable table headers: tappable on mobile */
.table thead th {
    min-height: 44px;
    padding: 10px 8px;
    cursor: pointer;
}

.sort-indicator {
    font-size: 1em;
    margin-left: 2px;
    user-select: none;
}

.class-stats a.stats-link {
    display: inline-block;
    color: #1e293b;
    text-decoration: none;
    font-weight: 600;
    margin-right: 1rem;
    margin-bottom: 0.25rem;
    cursor: pointer;
}
.class-stats a.stats-link:hover {
    text-decoration: underline;
}
.class-stats a.stats-link:last-child {
    margin-right: 0;
}

.cell-nowrap {
    white-space: nowrap;
}

/* Main layout: News24-style PC with ad slots (top banner + left | center | right) */
.main-content {
    display: block;
    width: 100%;
}

.ad-banner-top {
    width: 100%;
    min-height: 40px;
    background: #e8eef4;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: center;
}

.ad-banner-top .ad-slot-placeholder {
    width: 100%;
    max-width: 970px;
    min-height: 40px;
}

.layout-three-col {
    display: flex;
    width: 100%;
    max-width: 100%;
}

.ad-column-left,
.ad-column-right {
    flex-shrink: 0;
    width: 160px;
    min-width: 160px;
    padding: 1rem 0.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: #f0f4f8;
    border-left: 1px solid var(--border-color);
}

.ad-column-left {
    border-left: none;
    border-right: 1px solid var(--border-color);
}

.main-column {
    flex: 1 1 auto;
    min-width: 0;
    display: block;
}

.main-column .container {
    overflow: visible;
}

/* Ad slot placeholders (replace with ad code; hide .ad-slot-placeholder when using real ads) */
.ad-slot {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #888;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.ad-slot-placeholder {
    background: #e8ecf0;
    border: 1px dashed #b0b8c0;
    border-radius: 4px;
}

.ad-slot-vertical {
    min-height: 320px;
    width: 100%;
    max-width: 160px;
}

@media (max-width: 1023px) {
    .ad-column-left,
    .ad-column-right {
        display: none;
    }
}

@media (max-width: 768px) {
    .ad-banner-top {
        min-height: 32px;
    }
    .ad-banner-top .ad-slot-placeholder {
        min-height: 32px;
    }
}

/* Header */
.site-header {
    background: #001f3f; /* Navy blue */
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding: 1rem 0;
}

@media (max-width: 768px) {
    .site-header {
        padding: 0.6rem 0;
        min-height: auto;
    }
}

.site-header .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

@media (max-width: 768px) {
    .site-header .container {
        gap: 0.5rem;
        padding: 0 0.75rem;
        flex-wrap: nowrap;
        overflow: visible;
    }
    
    .logo {
        flex-shrink: 0;
        min-width: auto;
    }
    
    .header-auth {
        flex-shrink: 0;
        min-width: 0;
    }
}

.logo img {
    height: 40px;
    width: auto;
    max-width: none;
    object-fit: contain;
}

@media (max-width: 768px) {
    .logo img {
        height: 30px;
    }
}

.header-refresh-btn {
    margin-left: 0.75rem;
    padding: 0.35rem 0.65rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: #fff;
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 6px;
    text-decoration: none;
    white-space: nowrap;
}
.header-refresh-btn:hover {
    background: rgba(255, 255, 255, 0.25);
    color: #fff;
}

.main-nav {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex: 1;
}

.main-nav a {
    color: #ffffff; /* White text for navy background */
    text-decoration: none;
    font-weight: 500;
    transition: opacity 0.2s;
}

.main-nav a:hover {
    opacity: 0.8;
    text-decoration: underline;
}

/* Header Auth (Login Status / Login Box) - Far right, next to menu */
.header-auth {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-right: 0.75rem;
}

@media (max-width: 768px) {
    .header-auth {
        gap: 0.5rem;
        margin-right: 0.25rem;
        flex-shrink: 0;
        min-width: 0;
    }
    
    .header-auth .btn-primary {
        flex-shrink: 0 !important;
        min-width: auto !important;
        max-width: none !important;
        width: auto !important;
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
        font-size: 0.75rem !important;
        padding: 0.5rem 0.8rem !important;
    }
}

@media (max-width: 480px) {
    .header-auth .btn-primary {
        font-size: 0.7rem !important;
        padding: 0.4rem 0.7rem !important;
        white-space: nowrap !important;
    }
}

#loggedInStatus {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: nowrap;
    margin-left: 0;
}


.user-info {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    text-align: right;
    line-height: 1.3;
    margin-left: 50px; /* Move Name and SAS ID left 50px - applies to all screen sizes */
}

.user-name {
    color: #ffffff;
    font-weight: 600;
    white-space: nowrap;
}

.user-name-value {
    color: #ffffff !important; /* White for name */
    font-size: inherit; /* Same font size as parent (.user-name) */
    font-weight: inherit; /* Same font weight as parent */
}

.user-sas-id {
    color: rgba(255, 255, 255, 0.85);
    white-space: nowrap;
}

.sas-id-value {
    color: #ffffff; /* White for SAS ID number */
}

@media (max-width: 768px) {
    #loggedInStatus {
        gap: 0.5rem;
        flex-wrap: nowrap;
    }
    
    .user-info {
        flex-direction: column; /* Stack vertically: Name on top, SAS ID below */
        align-items: flex-end;
        gap: 0.2rem;
        line-height: 1.2;
        margin-left: -70px !important; /* Move Welcome and SAS ID left 70px on mobile (40px + 20px + 10px) */
    }
    
    .user-name {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
    }
    
    .user-name-value {
        color: #ffffff !important; /* White for name */
        font-size: inherit !important; /* Same font size as .user-name */
        font-weight: inherit !important; /* Same font weight as .user-name */
    }
    
    .user-sas-id {
        font-size: 0.65rem !important;
        opacity: 1;
        color: rgba(255, 255, 255, 0.85) !important; /* White for SAS ID: text */
    }
    
    /* Ensure SAS ID number is white on mobile */
    .sas-id-value {
        color: #ffffff !important; /* White for SAS ID number - same as desktop */
    }
}


.btn-logout {
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: #ffffff; /* White text for navy background */
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    white-space: nowrap;
    transition: background 0.2s;
}

@media (max-width: 768px) {
    .btn-logout {
        padding: 0.35rem 0.6rem;
        font-size: 0.75rem;
        min-width: auto;
    }
}

.btn-logout:hover {
    background: rgba(255, 255, 255, 0.25);
}

.menu-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    transition: background 0.2s;
}

.menu-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    align-items: center;
    justify-content: center;
}

@media (max-width: 768px) {
    .menu-btn {
        padding: 0.4rem;
    }
    
    .menu-icon {
        width: 18px;
    }
}

.menu-icon {
    width: 20px;
    height: 2px;
    background: #ffffff; /* White for navy background */
    position: relative;
    display: block;
}

.menu-icon::before,
.menu-icon::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    height: 2px;
    background: #ffffff; /* White for navy background */
}

.menu-icon::before {
    top: -6px;
}

.menu-icon::after {
    top: 6px;
}

.nav-menu-overlay {
    display: none;
    flex-direction: column;
    position: absolute;
    top: 100%;
    right: 0;
    background: #001f3f;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
    padding: 0.5rem 0;
    min-width: 140px;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.nav-menu-overlay a {
    color: #fff;
    text-decoration: none;
    padding: 0.5rem 1rem;
    font-size: 0.95rem;
    -webkit-tap-highlight-color: rgba(255,255,255,0.2);
    touch-action: manipulation;
}
.nav-menu-overlay a:hover {
    background: rgba(255,255,255,0.1);
}
.site-header { position: relative; }

@media (max-width: 768px) {
    .nav-menu-overlay {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        min-width: auto;
        border-radius: 0;
        padding: 4rem 1rem 1rem;
        z-index: 9999;
        justify-content: flex-start;
        align-items: stretch;
        background: rgba(0,31,63,0.98);
    }
    .nav-menu-overlay a {
        padding: 1rem 1.25rem;
        font-size: 1.1rem;
        min-height: 44px;
        display: flex;
        align-items: center;
        border-bottom: 1px solid rgba(255,255,255,0.15);
    }
}

/* Buttons */
.btn-primary {
    background: var(--primary-color);
    color: var(--white);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: visible;
    text-overflow: clip;
}

@media (max-width: 768px) {
    .btn-primary {
        padding: 0.5rem 0.6rem;
        font-size: 0.7rem;
        min-width: auto;
        flex-shrink: 0;
        width: auto;
        max-width: none;
    }
}

@media (max-width: 480px) {
    .btn-primary {
        padding: 0.35rem 0.5rem;
        font-size: 0.65rem;
        min-width: auto;
        flex-shrink: 0;
        width: auto;
        max-width: none;
    }
}

.btn-primary:hover {
    opacity: 0.9;
}

.btn-secondary {
    background: transparent;
    color: var(--primary-color);
    border: 1px solid var(--primary-color);
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
}

.btn-tertiary {
    background: #ccc;
    color: var(--text-color);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
}

.btn-google {
    background: #DC143C;
    color: var(--white);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    width: 100%;
    margin-bottom: 0.5rem;
}

.btn-facebook {
    background: #1877F2;
    color: var(--white);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    width: 100%;
    margin-bottom: 0.5rem;
}

.btn-email {
    background: #808080;
    color: var(--white);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    width: 100%;
    margin-bottom: 0.5rem;
}

.btn-username {
    background: var(--primary-color);
    color: var(--white);
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    width: 100%;
    margin-bottom: 0.5rem;
}

/* Purple "Your Sailing Results" button in header */
.sailing-results-header-btn {
    background: #6B2C91;
    color: var(--white);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    padding: 0.5rem 1rem;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    margin-right: 0.75rem;
}

@media (max-width: 768px) {
    .sailing-results-header-btn {
        padding: 0.4rem 0.75rem;
        font-size: 12px;
    }
}

.sailing-results-header-btn:hover {
    background: #7B3CA1;
    border-color: rgba(255, 255, 255, 0.3);
}

/* Popup */
.popup-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.popup-container {
    background: var(--white);
    border-radius: 8px;
    padding: 2rem;
    max-width: 500px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    position: relative;
}

.popup-close {
    position: absolute;
    top: 1rem;
    right: 1rem;
    background: none;
    border: none;
    font-size: 2rem;
    cursor: pointer;
    color: var(--text-color);
}

.popup-state {
    display: block;
}

.popup-state.hidden {
    display: none;
}

.auth-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
}

.profile-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
}

.verification-options {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
}

.loading-spinner {
    border: 3px solid var(--border-color);
    border-top: 3px solid var(--primary-color);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: 0 auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Forms */
form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

input[type="text"],
input[type="email"],
select {
    padding: 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 1rem;
}

label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Responsive */
@media (max-width: 768px) {
    .main-nav {
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .popup-container {
        width: 95%;
        padding: 1.5rem;
    }
    
    /* Additional mobile header compactness */
    .container {
        padding: 0 0.75rem;
    }
    
    /* Very small screens - make header even more compact */
    @media (max-width: 480px) {
        .site-header {
            padding: 0.5rem 0;
        }
        
        .site-header .container {
            padding: 0 0.5rem;
            gap: 0.3rem;
        }
        
        #loggedInStatus {
            gap: 0.35rem;
        }
        
        .user-info {
            gap: 0.2rem;
            margin-left: -70px !important; /* Move Name and SAS ID left 70px on very small screens (40px + 20px + 10px) */
        }
        
        .user-name {
            font-size: 0.7rem !important;
        }
        
        .user-name-value {
            color: #ffffff !important; /* White for name */
            font-size: inherit !important; /* Same font size as .user-name */
            font-weight: inherit !important; /* Same font weight as .user-name */
        }
        
        .user-sas-id {
            font-size: 0.6rem !important;
            color: rgba(255, 255, 255, 0.85) !important; /* White for SAS ID: text */
        }
        
        /* Ensure SAS ID number is white on very small screens */
        .sas-id-value {
            color: #ffffff !important; /* White for SAS ID number */
        }
        
        .btn-logout {
            padding: 0.3rem 0.5rem;
            font-size: 0.7rem;
        }
        
        .logo img {
            height: 28px;
            width: auto;
            max-width: none;
        }
    }
}
```

---

## Layout structure summary

| Area | Selectors | Notes |
|------|-----------|--------|
| **Page** | `html`, `body`, `main` | Background `#f5f7fa`, transparent main, smooth scroll |
| **Content width** | `.container` | max-width 1100px, padding 12px (0.75rem on mobile) |
| **Cards** | `.card` | White, 10px radius, 18px padding, light shadow |
| **Content layout** | `.main-content`, `.layout-three-col`, `.main-column` | Full-width block; three-col flex with center column |
| **Ad slots** | `.ad-banner-top`, `.ad-column-left/right`, `.ad-slot*` | Top banner + side columns; side columns hidden &lt; 1024px |
| **Header** | `.site-header`, `.site-header .container` | Navy `#001f3f`, flex row, logo + nav + auth |
| **Nav** | `.main-nav`, `.nav-menu-overlay` | Flex links; overlay full-screen on mobile |
| **Tables** | `.table-container`, `.table thead th`, `.hide-mobile`, `.cell-nowrap` | Scroll wrapper, 44px th, hide columns &lt; 600px |
| **Stats links** | `.class-stats a.stats-link` | Inline-block stat links in stats card |

Additional page-specific layout (e.g. class hero, section titles) is in **`sailingsa/frontend/css/inline-styles.css`** or inline in `index.html` / `landing.html`.
