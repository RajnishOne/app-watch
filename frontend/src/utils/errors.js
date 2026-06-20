// Helper function to convert technical error messages to human-readable ones
export function getHumanReadableError(errorMessage) {
  if (!errorMessage) return 'An unknown error occurred';

  const errorLower = errorMessage.toLowerCase();

  // DNS/Network errors
  if (errorLower.includes('name resolution') ||
      errorLower.includes('failed to resolve') ||
      errorLower.includes('temporary failure in name resolution') ||
      errorLower.includes('dns') ||
      errorLower.includes('name resolution error')) {
    return 'Unable to connect to App Store. This is usually a temporary network issue. Please check your internet connection and try again in a few moments.';
  }

  if (errorLower.includes('connection') &&
      (errorLower.includes('refused') || errorLower.includes('timeout') || errorLower.includes('failed'))) {
    return 'Connection to App Store failed. Please check your internet connection and try again.';
  }

  if (errorLower.includes('timeout') || errorLower.includes('timed out')) {
    return 'Request timed out. The App Store may be slow or unavailable. Please try again.';
  }

  if (errorLower.includes('max retries exceeded')) {
    return 'Unable to reach App Store after multiple attempts. This is usually temporary. Please try again in a few moments.';
  }

  // HTTP errors
  if (errorLower.includes('404') || errorLower.includes('not found')) {
    return 'App not found in App Store. Please verify the App Store ID is correct.';
  }

  if (errorLower.includes('403') || errorLower.includes('forbidden')) {
    return 'Access denied. The App Store may be blocking the request.';
  }

  if (errorLower.includes('429') || errorLower.includes('too many requests')) {
    return 'Too many requests. Please wait a moment before trying again.';
  }

  if (errorLower.includes('500') || errorLower.includes('internal server error')) {
    return 'App Store server error. Please try again later.';
  }

  if (errorLower.includes('502') || errorLower.includes('bad gateway')) {
    return 'App Store is temporarily unavailable. Please try again in a few moments.';
  }

  if (errorLower.includes('503') || errorLower.includes('service unavailable')) {
    return 'App Store service is temporarily unavailable. Please try again later.';
  }

  // App-specific errors
  if (errorLower.includes('app not found in app store')) {
    return 'App not found in App Store. Please verify the App Store ID is correct.';
  }

  if (errorLower.includes('app store id') && errorLower.includes('required')) {
    return 'App Store ID is required. Please enter a valid App Store ID.';
  }

  if (errorLower.includes('webhook') && errorLower.includes('failed')) {
    return 'Failed to send notification. Please check your webhook configuration.';
  }

  if (errorLower.includes('notification') && errorLower.includes('failed')) {
    return 'Failed to send notification. Please check your notification settings.';
  }

  // Generic fallback - return original if no match, but clean it up a bit
  // Remove technical details like connection pool info
  let cleaned = errorMessage;
  if (cleaned.includes('HTTPSConnectionPool')) {
    cleaned = cleaned.replace(/HTTPSConnectionPool\([^)]+\):\s*/g, '');
  }
  if (cleaned.includes('Caused by')) {
    const causedByIndex = cleaned.indexOf('Caused by');
    cleaned = cleaned.substring(0, causedByIndex).trim();
  }

  // If cleaned message is still very technical, provide a generic message
  if (cleaned.length > 200 || (cleaned.includes('[') && cleaned.includes(']'))) {
    return 'An error occurred while checking the app. Please try again. If the problem persists, check your network connection.';
  }

  return cleaned || 'An error occurred. Please try again.';
}
