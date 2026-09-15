const API = "http://127.0.0.1:5000"

Vue.createApp({
  data() {
    return {
        logs: [],
        searchQuery: '',
        loading: false,
        lastUpdated: null,
        autoRefresh: false,
        refreshTimer: null,
        searchTimer: null,

        showFilter: {},
        filters: {},
        isLogin: false,
        username: ''
    }
  },

  created() {
    const keys = ['time', 'username', 'floor', 'ip', 'field', 'old_value', 'new_value']
    keys.forEach(key => {
      this.showFilter[key] = false
      this.filters[key] = []
    })
  },

  computed: {
    activeFiltersCount() {
      return Object.values(this.filters).reduce((sum, arr) => sum + arr.length, 0)
    },

    filteredLogs() {
      return this.logs.filter(log => {
        if (this.searchQuery) {
          const q = this.searchQuery.toLowerCase()
          const match = Object.values(log).some(val => 
            String(val ?? '').toLowerCase().includes(q)
          )
          if (!match) return false
        }
        
        const keys = ['time', 'username', 'floor', 'ip', 'field', 'old_value', 'new_value']
        return keys.every(key => {
          const selected = this.filters[key]
          if (selected.length === 0) return true
          return keys.every(key => {
            const selected = this.filters[key]
            if (selected.length === 0) return true

            if (key === 'floor') {
              const combined = (log.site || '') + '-' + (log.floor || '')
              return selected.includes(combined)
            }

            return selected.includes(log[key] ?? '')
          })
        })
      })
    },

    // ⭐ 使用 computed 快取 uniqueValues，避免每次渲染都計算
      uniqueValuesMap() {
        const keys = ['time', 'username', 'floor', 'ip', 'field', 'old_value', 'new_value']
        const map = {}

        keys.forEach(key => {

          if (key === 'floor') {
            // ⭐ Site + Floor 組合
            map[key] = [
              ...new Set(
                this.logs.map(l => (l.site || '') + '-' + (l.floor || ''))
              )
            ].sort((a, b) => {
              if (a === '') return 1
              if (b === '') return -1
              return a.localeCompare(b, 'zh-TW')
            })
          } else {
            map[key] = [
              ...new Set(this.logs.map(l => l[key] ?? ''))
            ].sort((a, b) => {
              if (a === '') return 1
              if (b === '') return -1
              return String(a).localeCompare(String(b), 'zh-TW')
            })
          }

        })

        return map
      }
  },

  methods: {
    formatTime(timeStr) {
      if (!timeStr) return '-'
      try {
        const date = new Date(timeStr)
        return date.toLocaleString('zh-TW', {
          month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit',
          hour12: false
        }).replace(/\//g, '-')
      } catch {
        return timeStr
      }
    },

    toggleFilter(key) {
      const keys = ['time', 'username', 'floor', 'ip', 'field', 'old_value', 'new_value']
      keys.forEach(k => {
        if (k !== key) this.showFilter[k] = false
      })
      this.$nextTick(() => {
        this.showFilter[key] = !this.showFilter[key]
      })
    },

    resetFilters() {
      const keys = ['time', 'username', 'floor', 'ip', 'field', 'old_value', 'new_value']
      keys.forEach(key => {
        this.filters[key] = []
      })
      this.searchQuery = ''
    },

    async fetchLogs() {
      this.loading = true
      try {
        const q = this.searchQuery.trim()
        const url = q 
          ? `${API}/api/audit_logs/search?q=${encodeURIComponent(q)}`
          : `${API}/api/audit_logs`
        
        const res = await fetch(url)
        if (!res.ok) throw new Error('載入失敗')
        
        this.logs = await res.json()
        this.lastUpdated = new Date().toLocaleTimeString('zh-TW', { 
          hour: '2-digit', minute: '2-digit' 
        })
      } catch (err) {
        console.error('Fetch error:', err)
        if (this.logs.length === 0) {
          this.logs = [
            {id:1,time:'2024-03-21T14:30:22',username:'詹睿穎',floor:'3F',ip:'192.168.1.105',field:'shift_type',old_value:'RR',new_value:'NT'},
            {id:2,time:'2024-03-21T14:28:15',username:'Admin',floor:'2F',ip:'192.168.1.101',field:'status',old_value:'offline',new_value:'online'},
            {id:3,time:'2024-03-21T14:25:03',username:'System',floor:'B1',ip:'10.0.0.88',field:'threshold',old_value:'',new_value:'85'},
          ]
        }
      } finally {
        this.loading = false
      }
    },

    setupAutoRefresh() {
      if (this.refreshTimer) clearInterval(this.refreshTimer)
      if (this.autoRefresh) {
        this.refreshTimer = setInterval(() => this.fetchLogs(), 30000)
      }
    },

    setupClickOutside() {
      document.addEventListener('click', e => {
        if (!e.target.closest('th')) {
          const keys = ['time', 'username', 'floor', 'ip', 'field', 'old_value', 'new_value']
          keys.forEach(k => {
            if (this.showFilter[k]) this.showFilter[k] = false
          })
        }
      }, { passive: true })
    },

    goBack() {
      // ⭐ 存登入狀態
      localStorage.setItem('isLogin', 'true')

      // ⭐ 存使用者名稱
      localStorage.setItem('username', this.username)
      // 或跳轉到指定頁面
      window.location.href = 'index.html'; // 替換為您的首頁 URL
      
    }
  },

  watch: {
    searchQuery() {
      clearTimeout(this.searchTimer)
      this.searchTimer = setTimeout(() => this.fetchLogs(), 300)
    },
    autoRefresh() {
      this.setupAutoRefresh()
    }
  },

  mounted() {    
    const isLogin = localStorage.getItem('isLogin')
        // ⭐ 取得 username
    this.username = localStorage.getItem('username') || ''

    if (!isLogin) {
        window.location.href = "login.html"
        return
    }


    this.fetchLogs()
    this.setupAutoRefresh()
    this.setupClickOutside()
    
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        const keys = ['time', 'username', 'floor', 'ip', 'field', 'old_value', 'new_value']
        keys.forEach(k => {
          if (this.showFilter[k]) this.showFilter[k] = false
        })
      }
    })
  },

  beforeUnmount() {
    if (this.refreshTimer) clearInterval(this.refreshTimer)
    if (this.searchTimer) clearTimeout(this.searchTimer)
  }

}).mount('#app')