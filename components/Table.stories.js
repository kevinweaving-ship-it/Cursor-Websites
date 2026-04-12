/**
 * Table component — use table.table inside .table-container.
 * Min 44px header height; follow docs/design_system.md.
 */
export default {
  title: 'Components/Table',
  parameters: {
    docs: {
      description: {
        component: 'Data tables. Always wrap in .table-container. Use .hide-mobile for optional columns.',
      },
    },
  },
};

export const RegattaTable = () => `
  <div class="table-container" style="max-width: 600px;">
    <table class="table">
      <thead>
        <tr>
          <th>Event</th>
          <th>Date</th>
          <th class="hide-mobile">Club</th>
          <th>Entries</th>
          <th class="hide-mobile">Races</th>
        </tr>
      </thead>
      <tbody>
        <tr><td><a href="#">HYC Cape Classic 2026</a></td><td class="cell-nowrap">14–15 Mar 2026</td><td class="hide-mobile"><a href="#">HYC</a></td><td>24</td><td class="hide-mobile">8</td></tr>
        <tr><td><a href="#">Optimist Nationals</a></td><td class="cell-nowrap">20 Apr 2026</td><td class="hide-mobile"><a href="#">VYC</a></td><td>32</td><td class="hide-mobile">10</td></tr>
      </tbody>
    </table>
  </div>
`;

export const SailorsTable = () => `
  <div class="table-container" style="max-width: 500px;">
    <table class="table">
      <thead>
        <tr><th>Sailor</th><th>Races</th><th>Regattas</th><th>Last regatta</th></tr>
      </thead>
      <tbody>
        <tr><td><a href="#">Jane Doe</a></td><td>42</td><td>6</td><td><a href="#">Cape Classic 2025</a></td></tr>
        <tr><td><a href="#">John Smith</a></td><td>38</td><td>5</td><td>—</td></tr>
      </tbody>
    </table>
  </div>
`;
