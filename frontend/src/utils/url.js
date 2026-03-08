/**
 * Rewrites an internal MinIO URL (http://minio:9000/...) to a browser-accessible
 * path proxied through nginx (/minio/...).
 */
export function proxyVideoUrl(url) {
  if (!url) return url
  try {
    const u = new URL(url)
    return `/minio${u.pathname}`
  } catch {
    return url
  }
}
