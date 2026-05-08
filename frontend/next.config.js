/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Transpile Plotly (CommonJS module)
  transpilePackages: ['react-plotly.js', 'plotly.js'],
  webpack: (config) => {
    // Leaflet requires browser globals — exclude fs on client
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
    }
    return config
  },
}

module.exports = nextConfig
