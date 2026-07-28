import nextConfig from 'eslint-config-next/core-web-vitals'

const config = [
  ...nextConfig,
  {
    ignores: ['node_modules/**'],
  },
]

export default config
