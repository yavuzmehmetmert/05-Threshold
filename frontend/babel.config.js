module.exports = function (api) {
    api.cache(true);
    return {
        presets: ['babel-preset-expo'],
        plugins: [
            // Tamagui babel plugin Node.js 22+ ESM uyumsuzluğu nedeniyle devre dışı
            // Runtime modunda çalışacak, performans farkı minimal
            "react-native-reanimated/plugin",
        ],
    };
};
