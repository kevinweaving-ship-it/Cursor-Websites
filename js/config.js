/** Single source of truth. Cloud and Mac use same origin. */
const BASE_PATH = "/";
const BASE_URL = (typeof window !== 'undefined' && window.location) ? window.location.origin : '';
window.BASE_PATH = BASE_PATH;
window.BASE_URL = BASE_URL;