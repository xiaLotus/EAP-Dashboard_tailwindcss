const app = Vue.createApp({
  data() {
    return {
      headers: [
        { key: 'Local', label: '區域' },
        { key: 'Machine_ID', label: '機台編號' },
        { key: 'Internal_IP', label: 'IP 位址' },
        { key: 'Device_Name', label: '裝置名稱' },
        { key: '所在區域(柱位)', label: '所在區域' },
        { key: 'alive_or_dead', label: '狀態' }
      ],
      rows: [],
      countdown: 300,
      maxCountdown: 300,
      sortKey: '',
      sortAsc: true,
      groupedData: [],
      selectedGroup: 'Other',
      isRefreshing: false,

      currentSource: 'EAP',
      datasets: { EAP: [], EQP: [], Switch: [] },

      // 👇 虛擬清單設定
      rowHeight: 40,      // 依你的行高調整（px），你現在 padding 大約 36~44 可用 40
      keeps: 40,          // 可視 + 緩衝列數
      startIndex: 0,
      endIndex: 0,
      offsetY: 0,
      totalHeight: 0,
    };
  },

  computed: {
    minutes() { return Math.floor(this.countdown / 60).toString().padStart(2, '0'); },
    seconds() { return (this.countdown % 60).toString().padStart(2, '0'); },

    sortedRows() {
      if (!this.sortKey) return this.rows;
      const key = this.sortKey, asc = this.sortAsc;
      const arr = this.rows.slice(0);
      arr.sort((a, b) => {
        const A = a[key] ?? '', B = b[key] ?? '';
        if (A === B) return 0;
        return asc ? (A > B ? 1 : -1) : (A < B ? 1 : -1);
      });
      return arr;
    },

    // 👇 只取需要渲染的那段切片
    visibleRows() {
      const src = this.sortedRows;
      return src.slice(this.startIndex, this.endIndex).map((r, i) => ({
        // 穩定 key：來源加上索引（在 fetchAll 已加 __rowKey，這裡保險）
        __rowKey: r.__rowKey ?? `${this.currentSource}-${this.startIndex + i}`,
        ...r
      }));
    },

    filteredGroups() {
      return this.selectedGroup === 'all'
        ? this.groupedData
        : this.groupedData.filter(item => item.name === this.selectedGroup);
    },

    gridTemplate() {
      const n = this.headers.length || 1;
      return { gridTemplateColumns: `repeat(${n}, minmax(120px, 1fr))` };
    },
  },

  methods: {
    async fetchAll() {
      this.isRefreshing = true;
      try {
        const res = await fetch('http://127.0.0.1:5000/api/csv-data-all', { cache: 'no-store' });
        const data = await res.json();

        const normalize = (arr) => (Array.isArray(arr) ? arr : []).map(row => {
          const o = {};
          for (const h of this.headers) o[h.key] = row?.[h.key] ?? '';
          return o;
        });
        const withKey = (arr, prefix) => normalize(arr).map((r, i) => ({ __rowKey: `${prefix}-${i}`, ...r }));

        // 不做深層響應追蹤
        this.datasets = Vue.markRaw({
          EAP: withKey(data.EAP, 'E'),
          EQP: withKey(data.EQP, 'Q'),
          Switch: withKey(data.Switch, 'S'),
        });

        this.applySource(this.currentSource); // 只換參考
      } catch (e) {
        console.error('讀取 CSV 失敗：', e);
        this.datasets = Vue.markRaw({ EAP: [], EQP: [], Switch: [] });
        this.rows = [];
        this.resetVirtual();
      } finally {
        this.isRefreshing = false;
      }
    },

    setSource(src) {
      if (this.currentSource !== src) this.currentSource = src;
      // 讓繪製更順：下一個 frame 再切
      requestAnimationFrame(() => this.applySource(src));
    },

    applySource(src) {
      this.rows = this.datasets[src] || [];
      this.totalHeight = (this.sortedRows.length || 0) * this.rowHeight;
      this.recalcRange( (this.$refs.listWrap?.scrollTop) || 0 );
    },

    // ====== 虛擬清單核心 ======
    onScroll(e) {
      const top = e.target.scrollTop || 0;
      this.recalcRange(top);
    },
    recalcRange(scrollTop) {
      const est = Math.floor(scrollTop / this.rowHeight);
      const from = Math.max(est - Math.floor(this.keeps / 3), 0);
      const to = Math.min(from + this.keeps, this.sortedRows.length);
      this.startIndex = from;
      this.endIndex = to;
      this.offsetY = from * this.rowHeight;
    },
    resetVirtual() {
      this.startIndex = 0;
      this.endIndex = Math.min(this.keeps, (this.sortedRows.length || 0));
      this.offsetY = 0;
      this.totalHeight = (this.sortedRows.length || 0) * this.rowHeight;
    },
    // =========================

    async fetchJSON() {
      const previousSelection = this.selectedGroup;
      const res = await fetch('http://127.0.0.1:5000/api/device-summary');
      const raw = await res.json();

      const extractSortKeys = name => {
        if (name === 'Other') return [Infinity, Infinity, Infinity];
        const kMatch = name.match(/K(\d+)/i);
        const fMatch = name.match(/(\d+)F/);
        const parenMatch = name.match(/\((\d+)\)/);
        const kNum = kMatch ? parseInt(kMatch[1], 10) : Infinity;
        const fNum = fMatch ? parseInt(fMatch[1], 10) : Infinity;
        const areaNum = parenMatch ? parseInt(parenMatch[1], 10) : Infinity;
        return [kNum, fNum, areaNum];
      };

      this.groupedData = Object.entries(raw).map(([path, machines]) => {
        const rawName = path;
        const filename = path.includes('其他') ? 'Other' : path.split('\\').pop();
        const devices = Object.entries(machines).map(([name, info]) => ({
          name,
          ip: info.ip,
          count: info.count
        }));
        return { name: filename, rawName, devices };
      }).sort((a, b) => {
        const [kA, fA, pA] = extractSortKeys(a.name);
        const [kB, fB, pB] = extractSortKeys(b.name);
        return kA - kB || fA - fB || pA - pB;
      });

      const validNames = this.groupedData.map(g => g.name);
      this.selectedGroup = validNames.includes(previousSelection) ? previousSelection : 'Other';
    },

    toggleSort(key) {
      if (this.sortKey === key) {
        this.sortAsc = !this.sortAsc;
      } else {
        this.sortKey = key;
        this.sortAsc = true;
      }
      // 重新排序後要重設虛擬清單座標
      this.resetVirtual();
    },

    formatGroupName(filename) {
      if (!filename || typeof filename !== 'string') return '未知區網';
      if (filename.includes('其他')) return '其他';
      const match = filename.match(/([A-Z]+)[\\/]?(\d+F).*區網\((\d+)\)/);
      return match ? `${match[1]} ${match[2]} 區網${match[3]}` : filename;
    },

    async handleRefresh() {
      if (this.isRefreshing) return;   // 避免重複觸發
      this.isRefreshing = true;
      try {
        await Promise.all([
          this.fetchAll(),   // 左側表格資料
          this.fetchJSON()   // 右側彙總
        ]);
      } catch (e) {
        console.error(e);
      } finally {
        this.countdown = this.maxCountdown; // ← 重設回 300 秒（5:00）
        this.isRefreshing = false;          // 關閉旋轉
      }
    }
  },

  mounted() {
    // 綁定 scroll 事件（虛擬清單）
    this.$nextTick(() => {
      const el = this.$refs.listWrap;
      if (el) {
        el.addEventListener('scroll', this.onScroll, { passive: true });
      }
    });

    // 初始化資料
    this.fetchAll();
    this.fetchJSON();

    setInterval(() => {
      this.fetchAll();
      this.fetchJSON();
      this.countdown = this.maxCountdown;
    }, this.maxCountdown * 1000);

    setInterval(() => { if (this.countdown > 0) this.countdown--; }, 1000);
  },

  beforeUnmount() {
    const el = this.$refs.listWrap;
    if (el) el.removeEventListener('scroll', this.onScroll);
  }
});

app.mount('#app');
