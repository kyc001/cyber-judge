export function formatCount(value: number) {
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}w`;
  }

  return value.toLocaleString("zh-CN");
}

export function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function getPublicUrl(path: string) {
  if (typeof window === "undefined") {
    return path;
  }

  return `${window.location.origin}${path}`;
}
