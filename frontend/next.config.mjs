/** @type {import('next').NextConfig} */
const nextConfig = {
  // Hasil build berupa file statis di folder out/, siap diunggah ke S3
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
