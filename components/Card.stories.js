/**
 * Card component — follows docs/design_system.md.
 * Use .card for all content boxes; optional h2.section-title, .table-container.
 */
export default {
  title: 'Components/Card',
  parameters: {
    docs: {
      description: {
        component: 'Reusable card. Class: .card. Do not modify header/footer.',
      },
    },
  },
};

export const WithTitle = () => `
  <div class="card" style="max-width: 400px;">
    <h2 class="section-title">Regattas</h2>
    <p>Card body. Use for sections with optional table below.</p>
  </div>
`;

export const WithTable = () => `
  <div class="card" style="max-width: 500px;">
    <h2 class="section-title">Regattas</h2>
    <div class="table-container">
      <table class="table">
        <thead>
          <tr><th>Event</th><th>Date</th><th class="hide-mobile">Club</th></tr>
        </thead>
        <tbody>
          <tr><td><a href="#">HYC Cape Classic 2026</a></td><td class="cell-nowrap">14–15 Mar 2026</td><td class="hide-mobile">HYC</td></tr>
          <tr><td><a href="#">Optimist Nationals</a></td><td class="cell-nowrap">20 Apr 2026</td><td class="hide-mobile">VYC</td></tr>
        </tbody>
      </table>
    </div>
  </div>
`;

export const StatsCard = () => `
  <div class="card stats-card" style="max-width: 400px;">
    <div class="class-stats">
      <a class="stats-link" href="#regattas">Regattas 12</a>
      <a class="stats-link" href="#clubs">Clubs 8</a>
      <a class="stats-link" href="#sailors">Sailors 45</a>
    </div>
  </div>
`;
