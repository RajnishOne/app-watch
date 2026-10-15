const assert = require('assert');
const { parseAppUrl, formatAppUrl } = require('./appUrlParser');

console.log('Running appUrlParser tests...');

// 1. Test Apple App Store URLs
const appleCases = [
  {
    url: 'https://apps.apple.com/us/app/chess-play-learn/id329218549',
    expected: { platform: 'ios', appStoreId: '329218549', country: 'us', isValid: true }
  },
  {
    url: 'https://apps.apple.com/app/id329218549',
    expected: { platform: 'ios', appStoreId: '329218549', country: null, isValid: true }
  },
  {
    url: 'https://apps.apple.com/gb/app/procreate-pocket/id916366649?platform=iphone',
    expected: { platform: 'ios', appStoreId: '916366649', country: 'gb', isValid: true }
  },
  {
    url: 'apps.apple.com/in/app/whatsapp-messenger/id310633997',
    expected: { platform: 'ios', appStoreId: '310633997', country: 'in', isValid: true }
  },
  {
    url: 'https://itunes.apple.com/us/app/keynote/id361285480',
    expected: { platform: 'ios', appStoreId: '361285480', country: 'us', isValid: true }
  }
];

appleCases.forEach((tc, idx) => {
  const result = parseAppUrl(tc.url);
  assert.strictEqual(result.platform, tc.expected.platform, `Apple Case ${idx + 1} platform mismatch`);
  assert.strictEqual(result.appStoreId, tc.expected.appStoreId, `Apple Case ${idx + 1} ID mismatch`);
  assert.strictEqual(result.country, tc.expected.country, `Apple Case ${idx + 1} country mismatch`);
  assert.strictEqual(result.isValid, tc.expected.isValid, `Apple Case ${idx + 1} validity mismatch`);
});
console.log('✓ All Apple App Store test cases passed.');

// 2. Test Google Play Store URLs
const googleCases = [
  {
    url: 'https://play.google.com/store/apps/details?id=com.chess',
    expected: { platform: 'android', appStoreId: 'com.chess', country: null, isValid: true }
  },
  {
    url: 'https://play.google.com/store/apps/details?id=com.spotify.music&hl=en&gl=US',
    expected: { platform: 'android', appStoreId: 'com.spotify.music', country: 'us', isValid: true }
  },
  {
    url: 'play.google.com/store/apps/details?id=org.mozilla.firefox',
    expected: { platform: 'android', appStoreId: 'org.mozilla.firefox', country: null, isValid: true }
  },
  {
    url: 'market://details?id=com.google.android.apps.messaging',
    expected: { platform: 'android', appStoreId: 'com.google.android.apps.messaging', country: null, isValid: true }
  }
];

googleCases.forEach((tc, idx) => {
  const result = parseAppUrl(tc.url);
  assert.strictEqual(result.platform, tc.expected.platform, `Google Case ${idx + 1} platform mismatch`);
  assert.strictEqual(result.appStoreId, tc.expected.appStoreId, `Google Case ${idx + 1} ID mismatch`);
  assert.strictEqual(result.country, tc.expected.country, `Google Case ${idx + 1} country mismatch`);
  assert.strictEqual(result.isValid, tc.expected.isValid, `Google Case ${idx + 1} validity mismatch`);
});
console.log('✓ All Google Play Store test cases passed.');

// 3. Test Invalid / Unsupported URLs
const invalidCases = [
  '',
  '   ',
  null,
  undefined,
  'https://github.com/microsoft/vscode',
  'https://www.google.com',
  'https://play.google.com/store/apps/details', // missing id
  'https://apps.apple.com/us/app/chess-play-learn' // missing /id...
];

invalidCases.forEach((url, idx) => {
  const result = parseAppUrl(url);
  assert.strictEqual(result.isValid, false, `Invalid Case ${idx + 1} should be invalid`);
  assert.strictEqual(result.appStoreId, '', `Invalid Case ${idx + 1} should have empty ID`);
});
console.log('✓ All Invalid / Unsupported test cases passed.');

// 4. Test formatAppUrl
assert.strictEqual(formatAppUrl('ios', '123456789', 'us'), 'https://apps.apple.com/us/app/id123456789');
assert.strictEqual(formatAppUrl('ios', '123456789', 'gb'), 'https://apps.apple.com/gb/app/id123456789');
assert.strictEqual(formatAppUrl('android', 'com.example.app'), 'https://play.google.com/store/apps/details?id=com.example.app');
console.log('✓ formatAppUrl tests passed.');

console.log('🎉 ALL TESTS PASSED SUCCESSFULLY!');
