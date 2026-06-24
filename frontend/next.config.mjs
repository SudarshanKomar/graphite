/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Next 16 uses Turbopack by default; no webpack overrides needed. The repo
  // lives on native WSL ext4, so file watching works without polling.
};

export default nextConfig;
