/** Optional: use only for new UI that should match design_system.md. Production pages use main.css. */
module.exports = {
  content: ['**/*.html', '**/*.js', 'components/**/*.js'],
  theme: {
    extend: {
      colors: {
        primary: '#6B2C91',
        secondary: '#DC143C',
        'header-bg': '#001f3f',
        'box-heading': '#001f3f',
        'box-body': '#334155',
      },
      maxWidth: {
        container: '1100px',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Oxygen',
          'Ubuntu',
          'Cantarell',
          'sans-serif',
        ],
      },
      borderRadius: {
        box: '8px',
      },
      minHeight: {
        touch: '44px',
      },
    },
  },
  plugins: [],
};
