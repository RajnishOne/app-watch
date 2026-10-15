/**
 * Utility functions for parsing and formatting App Store and Google Play URLs.
 */

/**
 * Parse an Apple App Store or Google Play Store URL.
 * Extracts platform ('ios' | 'android'), appStoreId / packageId, and optional country code.
 *
 * @param {string} rawUrl - The URL entered by the user
 * @returns {{
 *   platform: 'ios' | 'android' | null,
 *   appStoreId: string,
 *   country: string | null,
 *   isValid: boolean,
 *   error: string | null
 * }}
 */
export function parseAppUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') {
    return {
      platform: null,
      appStoreId: '',
      country: null,
      isValid: false,
      error: null
    };
  }

  const trimmed = rawUrl.trim();
  if (!trimmed) {
    return {
      platform: null,
      appStoreId: '',
      country: null,
      isValid: false,
      error: null
    };
  }

  // Prepend https:// if protocol is missing to help URL parsing
  let normalized = trimmed;
  if (!/^https?:\/\//i.test(normalized) && !/^market:\/\//i.test(normalized)) {
    normalized = 'https://' + normalized;
  }

  // 1. Google Play Store check
  // Supported formats:
  // - https://play.google.com/store/apps/details?id=com.example.app
  // - https://play.google.com/store/apps/details?id=com.example.app&hl=en&gl=US
  // - market://details?id=com.example.app
  // - play.google.com/store/apps/details?id=com.example.app
  if (/play\.google\.com/i.test(normalized) || /^market:\/\/details/i.test(normalized)) {
    let id = null;
    let country = null;

    if (/^market:\/\//i.test(normalized)) {
      const matchId = normalized.match(/[?&]id=([a-zA-Z0-9._-]+)/i);
      if (matchId) id = matchId[1];
    } else {
      try {
        const parsed = new URL(normalized);
        id = parsed.searchParams.get('id');
        const gl = parsed.searchParams.get('gl');
        if (gl && /^[a-zA-Z]{2}$/.test(gl)) {
          country = gl.toLowerCase();
        }
      } catch {
        const matchId = normalized.match(/[?&]id=([a-zA-Z0-9._-]+)/i);
        if (matchId) id = matchId[1];
        const matchGl = normalized.match(/[?&]gl=([a-zA-Z]{2})/i);
        if (matchGl) country = matchGl[1].toLowerCase();
      }
    }

    if (id && /^[a-zA-Z0-9._-]+$/.test(id)) {
      return {
        platform: 'android',
        appStoreId: id,
        country: country || null,
        isValid: true,
        error: null
      };
    } else {
      return {
        platform: 'android',
        appStoreId: '',
        country: country || null,
        isValid: false,
        error: 'Google Play URL is missing a valid package ID (e.g., ?id=com.example.app)'
      };
    }
  }

  // 2. Apple App Store check
  // Supported formats:
  // - https://apps.apple.com/us/app/app-name/id123456789
  // - https://apps.apple.com/app/id123456789
  // - https://apps.apple.com/gb/app/id123456789?platform=iphone
  // - https://itunes.apple.com/us/app/app-name/id123456789
  // - apps.apple.com/app/id123456789
  if (/apps\.apple\.com/i.test(normalized) || /itunes\.apple\.com/i.test(normalized)) {
    const idMatch = normalized.match(/\/id(\d+)/i) || normalized.match(/[?&]id=(\d+)/i);
    const countryMatch = normalized.match(/(?:apps|itunes)\.apple\.com\/([a-zA-Z]{2})\//i);

    if (idMatch && idMatch[1]) {
      return {
        platform: 'ios',
        appStoreId: idMatch[1],
        country: countryMatch ? countryMatch[1].toLowerCase() : null,
        isValid: true,
        error: null
      };
    } else {
      return {
        platform: 'ios',
        appStoreId: '',
        country: countryMatch ? countryMatch[1].toLowerCase() : null,
        isValid: false,
        error: 'App Store URL is missing a valid numeric ID (e.g., /id123456789)'
      };
    }
  }

  // Unsupported URL
  return {
    platform: null,
    appStoreId: '',
    country: null,
    isValid: false,
    error: 'Only Apple App Store and Google Play Store URLs are supported. Other URLs will not work.'
  };
}

/**
 * Format a default URL for an existing app based on its platform and ID.
 */
export function formatAppUrl(platform, appStoreId, country = 'us') {
  if (!appStoreId) return '';
  if (platform === 'android') {
    return `https://play.google.com/store/apps/details?id=${appStoreId}`;
  }
  const countryCode = (country && country.trim()) ? country.trim().toLowerCase() : 'us';
  return `https://apps.apple.com/${countryCode}/app/id${appStoreId}`;
}
