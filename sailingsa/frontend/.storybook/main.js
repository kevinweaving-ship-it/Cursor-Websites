/** @type { import('@storybook/html-vite').StorybookConfig } */
const config = {
  stories: ['../components/**/*.stories.@(js|mdx)'],
  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
  ],
  framework: {
    name: '@storybook/html-vite',
    options: {},
  },
  staticDirs: ['../assets'],
};

export default config;
