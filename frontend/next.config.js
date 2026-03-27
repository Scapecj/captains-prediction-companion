/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // NOTE: WebSocket proxying is handled by custom server.js
  // Do NOT use rewrites for /ws/* as it conflicts with the custom server
}

module.exports = nextConfig
