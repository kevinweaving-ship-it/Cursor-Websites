/**
 * EventCard — .event-card used on /events page.
 * Styles are in api.py (inline) and main.css. Structure only here for reference.
 */
export default {
  title: 'Components/EventCard',
  parameters: {
    docs: {
      description: {
        component: 'Event card for /events. Upcoming = green tint; past = red; past with results = darker red.',
      },
    },
  },
};

export const Upcoming = () => {
  const style = 'background: #dcfce7; border: 2px solid #22c55e; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.5rem; max-width: 380px; display: flex; flex-direction: column; gap: 0.35rem;';
  return `
  <div class="event-card" style="${style}">
    <span class="event-card-header"><h3>ILCA Nationals 2026</h3></span>
    <span class="event-date">Thu 30 Apr 2026 18:00 – Sun 03 May 2026 18:00</span>
    <div class="event-card-body">
      <span class="event-type-line"><span class="event-type">Nationals</span></span>
      <span class="event-club">Host: HYC (Hermanus Yacht Club)</span>
      <a href="#" class="event-details-btn">Details</a>
    </div>
  </div>
  `;
};

export const PastWithResults = () => {
  const style = 'background: #7a1c1c; border: 2px solid #ef4444; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.5rem; max-width: 380px; color: #fff;';
  return `
  <div class="event-card event-card-has-results" style="${style}">
    <span class="event-card-header"><h3 style="color:#fff;">Cape Classic 2025</h3></span>
    <span class="event-date" style="color:#fecaca;">Sat 15 Mar 2025</span>
    <div class="event-card-body">
      <span class="event-type">Regional</span>
      <span class="event-result-line"><a href="#" class="event-result-yes">✓</a> Results</span>
    </div>
  </div>
  `;
};
