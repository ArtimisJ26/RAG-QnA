/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
        basePath: false,
      },
    ];
  },
  experimental: {
    largePageDataBytes: 128 * 100000,
    proxyTimeout: 120000, // 2 minutes
    serverComponentsExternalPackages: ['chrome-aws-lambda']
  },
  api: {
    bodyParser: {
      sizeLimit: '50mb'
    },
    responseLimit: '50mb',
    externalResolver: true,
  },
  httpAgentOptions: {
    keepAlive: true,
  },
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    // Increase the size limit for webpack
    config.performance = {
      ...config.performance,
      maxAssetSize: 50000000, // 50MB
      maxEntrypointSize: 50000000, // 50MB
    };
    return config;
  },
};

module.exports = nextConfig; 