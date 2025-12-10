// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname, {
    // [Web-only] Enables CSS support in Metro.
    isCSSEnabled: true,
});

// Tamagui metro plugin Node.js 22+ ESM uyumsuzluğu nedeniyle devre dışı
// Tamagui runtime modunda çalışacak, performans farkı minimal
module.exports = config;

