import { describe, it, expect } from 'vitest'
import { proxyVideoUrl } from '../utils/url'

describe('proxyVideoUrl', () => {
  it('rewrites minio hostname to /minio proxy path', () => {
    expect(proxyVideoUrl('http://minio:9000/bucket/project/video.mp4'))
      .toBe('/minio/bucket/project/video.mp4')
  })

  it('preserves the full pathname', () => {
    expect(proxyVideoUrl('http://minio:9000/bucket/proj/dubbed_abc123.mp4'))
      .toBe('/minio/bucket/proj/dubbed_abc123.mp4')
  })

  it('rewrites any valid http URL', () => {
    expect(proxyVideoUrl('http://localhost:9000/files/audio.wav'))
      .toBe('/minio/files/audio.wav')
  })

  it('returns null unchanged', () => {
    expect(proxyVideoUrl(null)).toBeNull()
  })

  it('returns undefined unchanged', () => {
    expect(proxyVideoUrl(undefined)).toBeUndefined()
  })

  it('returns an invalid URL string unchanged', () => {
    expect(proxyVideoUrl('not-a-url')).toBe('not-a-url')
  })

  it('handles URLs with query strings by stripping them (URL.pathname excludes query)', () => {
    const result = proxyVideoUrl('http://minio:9000/bucket/file.mp4?X-Amz-Signature=abc')
    expect(result).toBe('/minio/bucket/file.mp4')
  })
})
