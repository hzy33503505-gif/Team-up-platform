const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')
const REMINDER_KEY = 'contestReminders'
const REMINDER_WINDOW_DAYS = 7

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    myContests: [],
    reminderList: [],
    reminderMap: {}
  },

  onShow() {
    uiTheme.applyPageTheme(this)
    this.loadReminderMap()
    this.getMyContests()
  },

  loadReminderMap() {
    this.setData({
      reminderMap: wx.getStorageSync(REMINDER_KEY) || {}
    })
  },

  saveReminderMap(nextMap) {
    wx.setStorageSync(REMINDER_KEY, nextMap)
    this.setData({ reminderMap: nextMap })
  },

  getMyContests() {
    wx.request({
      url: `${BASE_URL}/my/contests`,
      method: 'GET',
      success: (res) => {
        const contests = Array.isArray(res.data) ? res.data : []
        const prepared = this.prepareContestReminders(contests)
        this.setData({
          myContests: prepared.contests,
          reminderList: prepared.reminders
        })
      },
      fail: () => {
        wx.showToast({ title: '我的竞赛加载失败', icon: 'none' })
      }
    })
  },

  prepareContestReminders(contests) {
    const today = this.startOfToday()
    const reminderMap = this.data.reminderMap || {}
    const normalized = contests.map((item) => {
      const deadlineInfo = this.getDeadlineInfo(item.deadline, today)
      const reminderEnabled = Boolean(reminderMap[item.id])
      const reminderStatus = this.buildReminderStatus(deadlineInfo, reminderEnabled)
      return {
        ...item,
        ...deadlineInfo,
        reminderEnabled,
        reminderStatus
      }
    })
    const reminders = normalized
      .filter((item) => item.reminderEnabled && item.canRemind && item.daysLeft >= 0 && item.daysLeft <= REMINDER_WINDOW_DAYS)
      .sort((a, b) => a.daysLeft - b.daysLeft)
    return { contests: normalized, reminders }
  },

  startOfToday() {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), now.getDate())
  },

  parseDeadline(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null
    const parts = value.split('-').map(Number)
    return new Date(parts[0], parts[1] - 1, parts[2])
  },

  getDeadlineInfo(deadline, today) {
    const date = this.parseDeadline(deadline)
    if (!date) {
      return {
        canRemind: false,
        daysLeft: null,
        deadlineText: '暂无明确报名截止时间',
        deadlineLevel: 'muted'
      }
    }
    const diff = Math.ceil((date.getTime() - today.getTime()) / 86400000)
    if (diff < 0) {
      return {
        canRemind: false,
        daysLeft: diff,
        deadlineText: `已于${deadline}截止`,
        deadlineLevel: 'ended'
      }
    }
    if (diff === 0) {
      return { canRemind: true, daysLeft: diff, deadlineText: '今天截止', deadlineLevel: 'urgent' }
    }
    if (diff <= 3) {
      return { canRemind: true, daysLeft: diff, deadlineText: `${diff}天后截止`, deadlineLevel: 'urgent' }
    }
    if (diff <= REMINDER_WINDOW_DAYS) {
      return { canRemind: true, daysLeft: diff, deadlineText: `${diff}天后截止`, deadlineLevel: 'warning' }
    }
    return { canRemind: true, daysLeft: diff, deadlineText: `${diff}天后截止`, deadlineLevel: 'normal' }
  },

  buildReminderStatus(deadlineInfo, enabled) {
    if (!deadlineInfo.canRemind) {
      return deadlineInfo.daysLeft === null ? '没有明确截止时间，暂不能设置提醒' : '报名已截止'
    }
    return enabled ? `已开启提醒，${deadlineInfo.deadlineText}` : '未开启提醒'
  },

  toggleReminder(e) {
    const id = e.currentTarget.dataset.id
    const target = this.data.myContests.find((item) => item.id === id)
    if (!target) return
    if (!target.canRemind) {
      wx.showToast({ title: target.daysLeft === null ? '暂无明确截止时间' : '报名已截止', icon: 'none' })
      return
    }
    const nextMap = { ...(this.data.reminderMap || {}) }
    if (nextMap[id]) {
      delete nextMap[id]
    } else {
      nextMap[id] = {
        enabled: true,
        deadline: target.deadline,
        name: target.name,
        createdAt: this.formatDateTime(new Date())
      }
    }
    this.saveReminderMap(nextMap)
    const prepared = this.prepareContestReminders(this.data.myContests)
    this.setData({
      myContests: prepared.contests,
      reminderList: prepared.reminders
    })
    wx.showToast({ title: nextMap[id] ? '已开启提醒' : '已关闭提醒', icon: 'success' })
  },

  goContestDetail(e) {
    wx.navigateTo({ url: `/pages/detail/detail?id=${e.currentTarget.dataset.id}` })
  },

  removeContest(e) {
    const id = e.currentTarget.dataset.id
    wx.request({
      url: `${BASE_URL}/my/contests/remove`,
      method: 'POST',
      data: { item_id: id },
      success: () => {
        const nextMap = { ...(this.data.reminderMap || {}) }
        delete nextMap[id]
        this.saveReminderMap(nextMap)
        this.getMyContests()
      },
      fail: () => {
        wx.showToast({ title: '删除失败', icon: 'none' })
      }
    })
  },

  formatDate(date) {
    const pad = (value) => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  },

  formatDateTime(date) {
    const pad = (value) => String(value).padStart(2, '0')
    return `${this.formatDate(date)} ${pad(date.getHours())}:${pad(date.getMinutes())}`
  }
})
