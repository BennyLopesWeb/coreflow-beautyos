module.exports = function(api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      // expo-router/babel está deprecated no SDK 50, babel-preset-expo já inclui
      'react-native-reanimated/plugin',
    ],
  };
};

