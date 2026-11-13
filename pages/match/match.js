const BASE_URL = 'http://127.0.0.1:8000'
const uiTheme = require('../../utils/theme')

const EMPTY_FORM = {
  title: '',
  contest_name: '',
  custom_contest_name: '',
  description: '',
  roles_text: '',
  tags_text: '',
  require_statement: false
}

const EMPTY_ROLE = {
  name: '',
  needed: 1,
  skills: ''
}

const INTEREST_TAGS = ['AI', '机器人', '数学建模', '电子设计', '创新创业', '软件开发', '机械制造', '材料', '外语', '商业分析', '产品设计', '科研训练']

Page({
  data: {
    themeMode: uiTheme.getThemeMode(),
    themeClass: uiTheme.getThemeClass(),
    isDarkTheme: uiTheme.getThemeMode() === 'dark',
    tabs: [
      { label: '招募大厅', value: 'recruit' },
      { label: '发布招募', value: 'publish' },
      { label: '我的申请', value: 'applications' },
      { label: '导师库', value: 'mentor' }
    ],
    activeTab: 'recruit',
    profile: {},
    profileContactText: '',
    profileReady: false,
    profileMissingText: '',
    allPosts: [],
    posts: [],
    recruitKeyword: '',
    recruitStatusOptions: ['全部状态', '招募中', '有空位', '已满员'],
    recruitStatusIndex: 0,
    recruitScopeOptions: ['全部范围', '同校区', '同学院', '同专业'],
    recruitScopeIndex: 0,
    recruitSortOptions: ['适配度优先', '最新发布', '缺口最多'],
    recruitSortIndex: 0,
    mentorList: [],
    mentorKeyword: '',
    mentorCampusOptions: ['全部校区'],
    mentorCollegeOptions: ['全部学院'],
    mentorOptionMap: {},
    selectedCampusIndex: 0,
    selectedCollegeIndex: 0,
    mentorPage: 1,
    mentorPageSize: 20,
    mentorTotal: 0,
    mentorTotalPages: 1,
    mentorLoading: false,
    mentorSourceText: '',
    mentorUpdatedAt: '',
    myRecruit: {
      sent: [],
      received: [],
      matched: [],
      my_posts: [],
      penalty: null
    },
    applicationText: {},
    form: { ...EMPTY_FORM },
    contestOptions: ['请选择目标竞赛', '自定义竞赛'],
    contestOptionItems: [],
    contestSelectorVisible: false,
    contestSearchKeyword: '',
    contestSearchResults: [],
    contestIndex: 0,
    roleRows: [{ ...EMPTY_ROLE }, { ...EMPTY_ROLE }],
    recruitTagOptions: INTEREST_TAGS.map((label) => ({ label, selected: false })),
    customRecruitTag: '',
    hitOptions: [],
    gateCampusOptions: ['不限校区'],
    gateCollegeOptions: ['不限学院'],
    gateMajorOptions: ['不限专业'],
    gateGradeOptions: ['不限年级', '大一', '大二', '大三', '大四', '研一', '研二', '研三', '博士'],
    gateCampusIndex: 0,
    gateCollegeIndex: 0,
    gateMajorIndex: 0,
    gateGradeIndex: 0,
    loadingPosts: false,
    publishing: false,
    refreshingMentors: false
  },

  onLoad() {
    uiTheme.applyPageTheme(this)
    this.loadProfile()
    this.loadHitOptions()
    this.loadContestOptions()
    this.loadMentorOptions()
    this.fetchPosts()
    this.fetchMentors()
  },

  onShow() {
    uiTheme.applyPageTheme(this)
    this.loadProfile()
    this.fetchPosts()
    this.fetchMyRecruitment()
  },

  loadProfile() {
    const profile = wx.getStorageSync('userProfile') || {}
    const required = [
      ['name', '姓名'],
      ['studentId', '学号'],
      ['campus', '校区'],
      ['college', '学院'],
      ['major', '专业'],
      ['grade', '年级']
    ]
    const missing = required.filter(([key]) => !profile[key]).map(([, label]) => label)
    this.setData({
      profile,
      profileContactText: this.buildContactText(profile),
      profileReady: missing.length === 0,
      profileMissingText: missing.join('、')
    })
  },

  loadHitOptions() {
    wx.request({
      url: `${BASE_URL}/hit/options`,
      method: 'GET',
      success: (res) => {
        const hitOptions = (res.data && res.data.campuses) || []
        this.setData({
          hitOptions,
          gateCampusOptions: ['不限校区', ...hitOptions.map((item) => item.name)]
        })
      }
    })
  },

  loadContestOptions(page = 1, collected = []) {
    wx.request({
      url: `${BASE_URL}/contests/search`,
      method: 'GET',
      data: {
        page,
        page_size: 50
      },
      success: (res) => {
        const data = res.data || {}
        const items = [...collected, ...((data.items || []).map((item) => ({
          id: item.id,
          name: item.name,
          category: item.category || '',
          status: item.status || '',
          source_name: item.source_name || ''
        })))]
        const totalPages = Number(data.total_pages || Math.ceil(Number(data.total || items.length) / Number(data.page_size || 50)) || 1)
        if (page < totalPages) {
          this.loadContestOptions(page + 1, items)
          return
        }
        const names = Array.from(new Set(items.map((item) => item.name).filter(Boolean)))
        const contestOptions = ['请选择目标竞赛', ...names, '自定义竞赛']
        this.setData({
          contestOptionItems: items,
          contestOptions,
          contestSearchResults: this.buildContestSearchResults(this.data.contestSearchKeyword, items, contestOptions)
        })
      }
    })
  },

  loadMentorOptions() {
    wx.request({
      url: `${BASE_URL}/mentors/options`,
      method: 'GET',
      success: (res) => {
        const campusColleges = (res.data && res.data.campus_colleges) || {}
        const mentorCampusOptions = ['全部校区', ...((res.data && res.data.campuses) || [])]
        this.setData({
          mentorCampusOptions,
          mentorCollegeOptions: ['全部学院'],
          mentorOptionMap: campusColleges
        })
      }
    })
  },

  changeTab(e) {
    const activeTab = e.currentTarget.dataset.value
    this.setData({ activeTab })
    if (activeTab === 'applications') this.fetchMyRecruitment()
    if (activeTab === 'mentor') this.fetchMentors()
  },

  goProfile() {
    wx.navigateTo({ url: '/pages/information/information' })
  },

  fetchPosts() {
    this.setData({ loadingPosts: true })
    wx.request({
      url: `${BASE_URL}/recruit/posts/query`,
      method: 'POST',
      data: { profile: this.data.profile || {} },
      success: (res) => {
        const allPosts = ((res.data && res.data.data) || []).map((item) => this.preparePost(item))
        this.setData({
          allPosts,
          posts: this.buildVisiblePosts(allPosts)
        })
      },
      fail: () => {
        wx.showToast({ title: '招募信息加载失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ loadingPosts: false })
      }
    })
  },

  preparePost(post) {
    const gates = post.gates || {}
    const currentUserId = String((this.data.profile || {}).studentId || (this.data.profile || {}).name || '').trim()
    const gatesText = [
      ...(gates.campuses || []),
      ...(gates.colleges || []),
      ...(gates.grades || []),
      ...(gates.majors || [])
    ].join('、') || '无硬性门槛'
    const roles = (post.roles || []).map((role) => {
      const remaining = Math.max(0, Number(role.needed || 0) - Number(role.filled || 0))
      return {
        ...role,
        confirmed_members: (role.confirmed_members || []).map((member) => ({
          ...member,
          isMe: String(member.user_id || '').trim() === currentUserId,
          contactText: this.buildContactText(member.profile || {})
        })),
        remaining,
        skillsText: (role.skills || []).join('、') || '发布者未限定技能',
        applyKey: `${post.id}-${role.id}`,
        statusText: remaining > 0 ? `还需${remaining}人` : '已确定'
      }
    })
    return {
      ...post,
      roles,
      gatesText,
      publisherContactText: this.buildContactText(post.publisher_profile || {}),
      needStatementText: gates.require_statement ? '需要申请说明' : '申请说明可选',
      matchDetailText: (post.match_details || []).map((item) => `${item.label}+${item.value}：${item.reason}`).join('；') || '完善个人信息后生成适配解释',
      matchReasonText: (post.match_reasons || []).join('；')
    }
  },

  buildContactText(profile) {
    const parts = []
    if (profile.studentId) parts.push(`学号：${profile.studentId}`)
    if (profile.phone && profile.phonePublic !== false) parts.push(`手机：${profile.phone}`)
    if (profile.qq && profile.qqPublic !== false) parts.push(`QQ：${profile.qq}`)
    return parts.join(' · ') || '暂无公开联系方式'
  },

  onRecruitKeywordInput(e) {
    this.setData({ recruitKeyword: e.detail.value }, () => this.applyRecruitFilters())
  },

  clearRecruitKeyword() {
    this.setData({ recruitKeyword: '' }, () => this.applyRecruitFilters())
  },

  onRecruitStatusChange(e) {
    this.setData({ recruitStatusIndex: Number(e.detail.value) }, () => this.applyRecruitFilters())
  },

  onRecruitScopeChange(e) {
    this.setData({ recruitScopeIndex: Number(e.detail.value) }, () => this.applyRecruitFilters())
  },

  onRecruitSortChange(e) {
    this.setData({ recruitSortIndex: Number(e.detail.value) }, () => this.applyRecruitFilters())
  },

  applyRecruitFilters() {
    this.setData({ posts: this.buildVisiblePosts(this.data.allPosts || []) })
  },

  buildVisiblePosts(sourcePosts) {
    const keyword = String(this.data.recruitKeyword || '').trim().toLowerCase()
    const status = this.data.recruitStatusOptions[this.data.recruitStatusIndex] || '全部状态'
    const scope = this.data.recruitScopeOptions[this.data.recruitScopeIndex] || '全部范围'
    const sort = this.data.recruitSortOptions[this.data.recruitSortIndex] || '适配度优先'
    const profile = this.data.profile || {}
    let posts = [...sourcePosts]

    if (keyword) {
      posts = posts.filter((post) => this.postSearchText(post).includes(keyword))
    }
    if (status === '招募中') {
      posts = posts.filter((post) => post.status === '招募中')
    } else if (status === '有空位') {
      posts = posts.filter((post) => Number(post.remaining || 0) > 0)
    } else if (status === '已满员') {
      posts = posts.filter((post) => Number(post.remaining || 0) === 0)
    }
    if (scope === '同校区' && profile.campus) {
      posts = posts.filter((post) => (post.publisher_profile || {}).campus === profile.campus)
    } else if (scope === '同学院' && profile.college) {
      posts = posts.filter((post) => (post.publisher_profile || {}).college === profile.college)
    } else if (scope === '同专业' && profile.major) {
      posts = posts.filter((post) => (post.publisher_profile || {}).major === profile.major)
    }

    posts.sort((a, b) => {
      if (sort === '最新发布') {
        return String(b.created_at || '').localeCompare(String(a.created_at || ''))
      }
      if (sort === '缺口最多') {
        return Number(b.remaining || 0) - Number(a.remaining || 0)
      }
      return Number(b.match_score || 0) - Number(a.match_score || 0)
    })
    return posts
  },

  postSearchText(post) {
    const rolesText = (post.roles || [])
      .map((role) => [role.name, role.direction, role.skillsText, role.statusText].filter(Boolean).join(' '))
      .join(' ')
    const publisher = post.publisher_profile || {}
    return [
      post.title,
      post.contest_name,
      post.description,
      post.tags_text,
      post.gatesText,
      post.status,
      publisher.name,
      publisher.campus,
      publisher.college,
      publisher.major,
      publisher.grade,
      rolesText
    ].filter(Boolean).join(' ').toLowerCase()
  },

  onApplicationInput(e) {
    const key = e.currentTarget.dataset.key
    this.setData({
      [`applicationText.${key}`]: e.detail.value
    })
  },

  sendApplication(e) {
    if (!this.data.profileReady) {
      wx.showModal({
        title: '请先补全个人信息',
        content: `缺少：${this.data.profileMissingText}`,
        confirmText: '去填写',
        success: (res) => {
          if (res.confirm) this.goProfile()
        }
      })
      return
    }
    const postId = e.currentTarget.dataset.postid
    const roleId = e.currentTarget.dataset.roleid
    const key = e.currentTarget.dataset.key
    wx.request({
      url: `${BASE_URL}/recruit/apply`,
      method: 'POST',
      data: {
        post_id: postId,
        role_id: roleId,
        statement: this.data.applicationText[key] || '',
        profile: this.data.profile
      },
      success: (res) => {
        wx.showToast({
          title: res.data.message || (res.data.ok ? '申请已发送' : '申请失败'),
          icon: res.data.ok ? 'success' : 'none'
        })
        if (res.data.ok) {
          this.setData({ [`applicationText.${key}`]: '' })
          this.fetchMyRecruitment()
        }
      },
      fail: () => {
        wx.showToast({ title: '发送失败', icon: 'none' })
      }
    })
  },

  onFormInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  onContestChange(e) {
    const contestIndex = Number(e.detail.value)
    const selected = this.data.contestOptions[contestIndex] || ''
    this.setData({
      contestIndex,
      'form.contest_name': selected && selected !== '请选择目标竞赛' && selected !== '自定义竞赛' ? selected : ''
    })
  },

  buildContestSearchResults(keyword = '', items = this.data.contestOptionItems, options = this.data.contestOptions) {
    const q = String(keyword || '').trim().toLowerCase()
    const seen = new Set()
    const normalized = (items || [])
      .map((item) => {
        const name = String(item.name || '').trim()
        if (!name || seen.has(name)) return null
        seen.add(name)
        return {
          key: item.id || name,
          id: item.id || '',
          name,
          index: Math.max(0, (options || []).indexOf(name)),
          desc: [item.category, item.status, item.source_name].filter(Boolean).join(' · ') || '竞赛库条目',
          haystack: `${name} ${item.category || ''} ${item.status || ''} ${item.source_name || ''}`.toLowerCase()
        }
      })
      .filter(Boolean)
    const filtered = q ? normalized.filter((item) => item.haystack.includes(q)) : normalized
    return filtered.slice(0, 80).map((item) => ({
      key: item.key,
      id: item.id,
      name: item.name,
      index: item.index,
      desc: item.desc,
      type: 'contest'
    }))
  },

  openContestSelector() {
    this.setData({
      contestSelectorVisible: true,
      contestSearchResults: this.buildContestSearchResults(this.data.contestSearchKeyword)
    })
  },

  closeContestSelector() {
    this.setData({ contestSelectorVisible: false })
  },

  stopTap() {},

  onContestSearchInput(e) {
    const keyword = e.detail.value
    this.setData({
      contestSearchKeyword: keyword,
      contestSearchResults: this.buildContestSearchResults(keyword)
    })
  },

  clearContestSearch() {
    this.setData({
      contestSearchKeyword: '',
      contestSearchResults: this.buildContestSearchResults('')
    })
  },

  selectContestOption(e) {
    const type = e.currentTarget.dataset.type
    if (type === 'placeholder') {
      this.setData({
        contestIndex: 0,
        'form.contest_name': '',
        'form.custom_contest_name': '',
        contestSelectorVisible: false
      })
      return
    }
    const customIndex = Math.max(0, this.data.contestOptions.indexOf('自定义竞赛'))
    if (type === 'custom') {
      const keyword = String(this.data.contestSearchKeyword || '').trim()
      this.setData({
        contestIndex: customIndex,
        'form.custom_contest_name': keyword,
        'form.contest_name': keyword,
        contestSelectorVisible: false
      })
      return
    }
    const name = String(e.currentTarget.dataset.name || '').trim()
    const index = Number(e.currentTarget.dataset.index)
    if (!name) return
    this.setData({
      contestIndex: index > 0 ? index : Math.max(0, this.data.contestOptions.indexOf(name)),
      'form.contest_name': name,
      'form.custom_contest_name': '',
      contestSelectorVisible: false
    })
  },

  onCustomContestInput(e) {
    this.setData({
      'form.custom_contest_name': e.detail.value,
      'form.contest_name': e.detail.value
    })
  },

  onRoleInput(e) {
    const index = Number(e.currentTarget.dataset.index)
    const field = e.currentTarget.dataset.field
    const roleRows = [...this.data.roleRows]
    roleRows[index] = {
      ...roleRows[index],
      [field]: e.detail.value
    }
    this.setData({ roleRows })
  },

  addRoleRow() {
    this.setData({
      roleRows: [...this.data.roleRows, { ...EMPTY_ROLE }]
    })
  },

  removeRoleRow(e) {
    const index = Number(e.currentTarget.dataset.index)
    if (this.data.roleRows.length <= 1) {
      wx.showToast({ title: '至少保留一个岗位', icon: 'none' })
      return
    }
    const roleRows = this.data.roleRows.filter((_, rowIndex) => rowIndex !== index)
    this.setData({ roleRows })
  },

  toggleRecruitTag(e) {
    const label = e.currentTarget.dataset.label
    const recruitTagOptions = this.data.recruitTagOptions.map((item) => (
      item.label === label ? { ...item, selected: !item.selected } : item
    ))
    this.setData({
      recruitTagOptions,
      'form.tags_text': this.selectedRecruitTags(recruitTagOptions).join('、')
    })
  },

  onCustomRecruitTagInput(e) {
    this.setData({ customRecruitTag: e.detail.value })
  },

  addCustomRecruitTag() {
    const value = String(this.data.customRecruitTag || '').trim()
    if (!value) return
    const exists = this.data.recruitTagOptions.some((item) => item.label === value)
    const recruitTagOptions = exists
      ? this.data.recruitTagOptions.map((item) => item.label === value ? { ...item, selected: true } : item)
      : [...this.data.recruitTagOptions, { label: value, selected: true }]
    this.setData({
      recruitTagOptions,
      customRecruitTag: '',
      'form.tags_text': this.selectedRecruitTags(recruitTagOptions).join('、')
    })
  },

  selectedRecruitTags(options = this.data.recruitTagOptions) {
    return options.filter((item) => item.selected).map((item) => item.label)
  },

  onRequireStatementChange(e) {
    this.setData({ 'form.require_statement': e.detail.value })
  },

  onGateCampusChange(e) {
    const index = Number(e.detail.value)
    const campus = this.data.hitOptions[index - 1]
    this.setData({
      gateCampusIndex: index,
      gateCollegeIndex: 0,
      gateMajorIndex: 0,
      gateCollegeOptions: ['不限学院', ...((campus && campus.colleges) || []).map((item) => item.name)],
      gateMajorOptions: ['不限专业']
    })
  },

  onGateCollegeChange(e) {
    const index = Number(e.detail.value)
    const campus = this.data.hitOptions[this.data.gateCampusIndex - 1]
    const college = campus && campus.colleges ? campus.colleges[index - 1] : null
    this.setData({
      gateCollegeIndex: index,
      gateMajorIndex: 0,
      gateMajorOptions: ['不限专业', ...((college && college.majors) || [])]
    })
  },

  onGateMajorChange(e) {
    this.setData({ gateMajorIndex: Number(e.detail.value) })
  },

  onGateGradeChange(e) {
    this.setData({ gateGradeIndex: Number(e.detail.value) })
  },

  polishRecruitment() {
    const roles = this.buildRolePayload()
    wx.request({
      url: `${BASE_URL}/recruit/polish`,
      method: 'POST',
      data: {
        ...this.data.form,
        contest_name: this.getSelectedContestName() || this.data.form.contest_name,
        roles_text: roles.map((role) => `${role.name}:${role.needed}:${role.skills.join('/')}`).join('；')
      },
      success: (res) => {
        const data = (res.data && res.data.data) || {}
        this.setData({
          'form.title': data.title || this.data.form.title,
          'form.description': data.summary || this.data.form.description
        })
        wx.showToast({ title: '已辅助整理', icon: 'success' })
      },
      fail: () => {
        wx.showToast({ title: '辅助整理失败', icon: 'none' })
      }
    })
  },

  publishRecruitment() {
    if (!this.data.profileReady) {
      wx.showModal({
        title: '请先补全个人信息',
        content: `缺少：${this.data.profileMissingText}`,
        confirmText: '去填写',
        success: (res) => {
          if (res.confirm) this.goProfile()
        }
      })
      return
    }
    const contestName = this.getSelectedContestName()
    const roles = this.buildRolePayload()
    const tagsText = this.selectedRecruitTags().join('、')
    if (!this.data.form.title || !this.data.form.description) {
      wx.showToast({ title: '请填写标题和需求描述', icon: 'none' })
      return
    }
    if (!contestName) {
      wx.showToast({ title: '请选择或填写目标竞赛', icon: 'none' })
      return
    }
    if (!roles.length) {
      wx.showToast({ title: '请至少填写一个岗位', icon: 'none' })
      return
    }
    if (!tagsText) {
      wx.showToast({ title: '请选择方向标签', icon: 'none' })
      return
    }

    this.setData({ publishing: true })
    wx.request({
      url: `${BASE_URL}/recruit/posts`,
      method: 'POST',
      data: {
        ...this.data.form,
        contest_name: contestName,
        roles,
        roles_text: roles.map((role) => `${role.name}:${role.needed}:${role.skills.join('/')}`).join('；'),
        tags_text: tagsText,
        profile: this.data.profile,
        gates: this.buildGates()
      },
      success: (res) => {
        wx.showToast({
          title: res.data.message || (res.data.ok ? '发布成功' : '发布失败'),
          icon: res.data.ok ? 'success' : 'none'
        })
        if (res.data.ok) {
          this.setData({
            form: { ...EMPTY_FORM },
            contestIndex: 0,
            contestSelectorVisible: false,
            contestSearchKeyword: '',
            contestSearchResults: this.buildContestSearchResults(''),
            roleRows: [{ ...EMPTY_ROLE }, { ...EMPTY_ROLE }],
            recruitTagOptions: INTEREST_TAGS.map((label) => ({ label, selected: false })),
            customRecruitTag: '',
            gateCampusIndex: 0,
            gateCollegeIndex: 0,
            gateMajorIndex: 0,
            gateGradeIndex: 0,
            gateCollegeOptions: ['不限学院'],
            gateMajorOptions: ['不限专业'],
            activeTab: 'recruit'
          })
          this.fetchPosts()
          this.fetchMyRecruitment()
        }
      },
      complete: () => {
        this.setData({ publishing: false })
      }
    })
  },

  getSelectedContestName() {
    const selected = this.data.contestOptions[this.data.contestIndex] || ''
    if (selected === '自定义竞赛') return String(this.data.form.custom_contest_name || '').trim()
    if (selected && selected !== '请选择目标竞赛') return selected
    return String(this.data.form.contest_name || '').trim()
  },

  buildRolePayload() {
    return (this.data.roleRows || [])
      .map((role, index) => {
        const name = String(role.name || '').trim()
        const skills = String(role.skills || '').split(/[，,、/；;\s]+/).filter(Boolean)
        const needed = Math.max(1, Number(role.needed || 1))
        if (!name && !skills.length) return null
        return {
          name: name || `岗位${index + 1}`,
          direction: name || `岗位${index + 1}`,
          needed,
          skills
        }
      })
      .filter(Boolean)
  },

  syncRecruitTagSelection(tagText) {
    const selected = new Set(String(tagText || '').split(/[，,、/；;\s]+/).filter(Boolean))
    const labels = new Set(INTEREST_TAGS)
    selected.forEach((label) => labels.add(label))
    return Array.from(labels).map((label) => ({
      label,
      selected: selected.has(label)
    }))
  },

  buildGates() {
    const campus = this.data.gateCampusOptions[this.data.gateCampusIndex]
    const college = this.data.gateCollegeOptions[this.data.gateCollegeIndex]
    const major = this.data.gateMajorOptions[this.data.gateMajorIndex]
    const grade = this.data.gateGradeOptions[this.data.gateGradeIndex]
    return {
      campuses: campus && campus !== '不限校区' ? [campus] : [],
      colleges: college && college !== '不限学院' ? [college] : [],
      majors: major && major !== '不限专业' ? [major] : [],
      grades: grade && grade !== '不限年级' ? [grade] : [],
      require_statement: this.data.form.require_statement
    }
  },

  fetchMyRecruitment() {
    if (!this.data.profile || !this.data.profile.studentId) return
    wx.request({
      url: `${BASE_URL}/recruit/my`,
      method: 'POST',
      data: { profile: this.data.profile },
      success: (res) => {
        const data = (res.data && res.data.data) || {}
        this.setData({
          myRecruit: this.prepareMyRecruitment(data)
        })
      }
    })
  },

  prepareMyRecruitment(data) {
    const statusMap = {
      pending: '待发布者处理',
      accepted: '已匹配',
      rejected: '已拒绝',
      role_full: '岗位已满',
      unbound: '已解绑'
    }
    const decorateApplication = (item) => ({
      ...item,
      statusText: statusMap[item.status] || item.status,
      applicantContactText: this.buildContactText(item.applicant_profile || {}),
      scoreDetailText: (item.score_detail || []).map((detail) => `${detail.label}+${detail.value}`).join('、')
    })
    return {
      sent: (data.sent || []).map(decorateApplication),
      received: (data.received || []).map(decorateApplication),
      matched: (data.matched || []).map((item) => this.preparePost(item)),
      my_posts: (data.my_posts || []).map((item) => this.preparePost(item)),
      penalty: data.penalty || null
    }
  },

  decideApplication(e) {
    const applicationId = e.currentTarget.dataset.id
    const decision = e.currentTarget.dataset.decision
    wx.request({
      url: `${BASE_URL}/recruit/applications/decide`,
      method: 'POST',
      data: {
        application_id: applicationId,
        decision,
        profile: this.data.profile
      },
      success: (res) => {
        wx.showToast({
          title: res.data.message || '已处理',
          icon: res.data.ok ? 'success' : 'none'
        })
        this.fetchPosts()
        this.fetchMyRecruitment()
      }
    })
  },

  requestUnbind(e) {
    wx.request({
      url: `${BASE_URL}/recruit/unbind`,
      method: 'POST',
      data: {
        post_id: e.currentTarget.dataset.postid,
        target_user_id: e.currentTarget.dataset.userid,
        profile: this.data.profile
      },
      success: (res) => {
        wx.showToast({ title: res.data.message || '已提交', icon: res.data.ok ? 'success' : 'none' })
        this.fetchPosts()
        this.fetchMyRecruitment()
      }
    })
  },

  complainMember(e) {
    wx.showModal({
      title: '投诉确认',
      content: '仅在已组队成员消极怠工时使用。除该成员外，所有队员都投诉后才会触发一个月组队限制。',
      confirmText: '提交投诉',
      success: (modal) => {
        if (!modal.confirm) return
        wx.request({
          url: `${BASE_URL}/recruit/complain`,
          method: 'POST',
          data: {
            post_id: e.currentTarget.dataset.postid,
            target_user_id: e.currentTarget.dataset.userid,
            reason: '消极怠工',
            profile: this.data.profile
          },
          success: (res) => {
            wx.showToast({ title: res.data.message || '已记录', icon: res.data.ok ? 'success' : 'none' })
            this.fetchMyRecruitment()
          }
        })
      }
    })
  },

  onMentorKeywordInput(e) {
    this.setData({ mentorKeyword: e.detail.value })
  },

  searchMentors() {
    this.fetchMentors(1)
  },

  clearMentorKeyword() {
    this.setData({ mentorKeyword: '' }, () => this.fetchMentors(1))
  },

  onMentorCampusChange(e) {
    const selectedCampusIndex = Number(e.detail.value)
    const campus = this.data.mentorCampusOptions[selectedCampusIndex] || '全部校区'
    const mentorCollegeOptions = campus === '全部校区'
      ? ['全部学院']
      : ['全部学院', ...((this.data.mentorOptionMap || {})[campus] || [])]
    this.setData({
      selectedCampusIndex,
      selectedCollegeIndex: 0,
      mentorCollegeOptions
    }, () => this.fetchMentors(1))
  },

  onMentorCollegeChange(e) {
    this.setData({ selectedCollegeIndex: Number(e.detail.value) }, () => this.fetchMentors(1))
  },

  fetchMentors(page = this.data.mentorPage || 1) {
    const campus = this.data.mentorCampusOptions[this.data.selectedCampusIndex] || '全部校区'
    const college = this.data.mentorCollegeOptions[this.data.selectedCollegeIndex] || '全部学院'
    this.setData({ mentorLoading: true })
    wx.request({
      url: `${BASE_URL}/mentors/search`,
      method: 'GET',
      data: {
        keyword: this.data.mentorKeyword || '',
        campus: campus === '全部校区' ? '' : campus,
        college: college === '全部学院' ? '' : college,
        page,
        page_size: this.data.mentorPageSize
      },
      success: (res) => {
        const data = res.data || {}
        const mentorList = (data.items || []).map((item) => ({
          ...item,
          tagText: item.research || '官方主页未公开研究方向',
          contactText: item.homepage ? '请进入官方主页查看联系方式' : '暂无官方主页链接'
        }))
        const total = Number(data.total || 0)
        const pageSize = Number(data.page_size || this.data.mentorPageSize || 20)
        this.setData({
          mentorList,
          mentorTotal: total,
          mentorPage: Number(data.page || page),
          mentorPageSize: pageSize,
          mentorTotalPages: Math.max(1, Math.ceil(total / pageSize)),
          mentorSourceText: `HIT 教师主页官网数据 · 共 ${total} 条`,
          mentorUpdatedAt: new Date().toLocaleString()
        })
      },
      fail: () => {
        wx.showToast({ title: '导师库加载失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ mentorLoading: false })
      }
    })
  },

  prevMentorPage() {
    if (this.data.mentorPage <= 1) return
    this.fetchMentors(this.data.mentorPage - 1)
  },

  nextMentorPage() {
    if (this.data.mentorPage >= this.data.mentorTotalPages) return
    this.fetchMentors(this.data.mentorPage + 1)
  },

  refreshMentors() {
    this.setData({ refreshingMentors: true })
    wx.request({
      url: `${BASE_URL}/mentors/refresh`,
      method: 'POST',
      success: (res) => {
        this.setData({
          mentorUpdatedAt: (res.data && res.data.refreshed_at) || ''
        })
        this.loadMentorOptions()
        this.fetchMentors(1)
        wx.showToast({ title: '导师库已刷新', icon: 'success' })
      },
      fail: () => {
        wx.showToast({ title: '刷新失败', icon: 'none' })
      },
      complete: () => {
        this.setData({ refreshingMentors: false })
      }
    })
  },

  openOfficialPage(e) {
    const url = e.currentTarget.dataset.url
    if (!url) {
      wx.showToast({ title: '暂无官方链接', icon: 'none' })
      return
    }
    wx.navigateTo({
      url: `/pages/webview/webview?url=${encodeURIComponent(url)}`
    })
  }
})
