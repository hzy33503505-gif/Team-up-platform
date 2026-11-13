const THEME_KEY = 'uiThemeMode'

const THEMES = {
  light: {
    className: 'theme-light',
    navigationBarBackgroundColor: '#67B3DB',
    navigationBarTextStyle: 'white',
    tabBarBackgroundColor: '#FEFFF7',
    tabBarColor: '#111111',
    tabBarSelectedColor: '#67B3DB',
    backgroundColor: '#F7FCFB'
  },
  dark: {
    className: 'theme-dark',
    navigationBarBackgroundColor: '#06141B',
    navigationBarTextStyle: 'white',
    tabBarBackgroundColor: '#11212D',
    tabBarColor: '#9BA8AB',
    tabBarSelectedColor: '#7FB7C8',
    backgroundColor: '#06141B'
  }
}

function normalizeThemeMode(mode) {
  return mode === 'dark' ? 'dark' : 'light'
}

function getThemeMode() {
  return normalizeThemeMode(wx.getStorageSync(THEME_KEY) || 'light')
}

function getThemeConfig(mode) {
  return THEMES[normalizeThemeMode(mode)]
}

function getThemeClass(mode) {
  return getThemeConfig(mode || getThemeMode()).className
}

function applyChrome(mode) {
  const theme = getThemeConfig(mode || getThemeMode())
  wx.setNavigationBarColor({
    frontColor: theme.navigationBarTextStyle === 'white' ? '#ffffff' : '#000000',
    backgroundColor: theme.navigationBarBackgroundColor,
    animation: {
      duration: 160,
      timingFunc: 'easeIn'
    }
  })
  if (wx.setBackgroundColor) {
    wx.setBackgroundColor({
      backgroundColor: theme.backgroundColor,
      backgroundColorTop: theme.backgroundColor,
      backgroundColorBottom: theme.backgroundColor
    })
  }
  if (wx.setTabBarStyle) {
    wx.setTabBarStyle({
      color: theme.tabBarColor,
      selectedColor: theme.tabBarSelectedColor,
      backgroundColor: theme.tabBarBackgroundColor,
      borderStyle: mode === 'dark' ? 'black' : 'white'
    })
  }
}

function setThemeMode(mode) {
  const nextMode = normalizeThemeMode(mode)
  wx.setStorageSync(THEME_KEY, nextMode)
  applyChrome(nextMode)
  return nextMode
}

function applyPageTheme(page) {
  const mode = getThemeMode()
  applyChrome(mode)
  page.setData({
    themeMode: mode,
    themeClass: getThemeClass(mode),
    isDarkTheme: mode === 'dark'
  })
}

module.exports = {
  THEME_KEY,
  getThemeMode,
  getThemeClass,
  applyChrome,
  setThemeMode,
  applyPageTheme
}
