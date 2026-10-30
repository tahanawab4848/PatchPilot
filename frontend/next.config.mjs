/** @type {import('next').NextConfig} */
const nextConfig = {
  // API URL is server-side configurable at runtime
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
  },
};

export default nextConfig;
