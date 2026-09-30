const app = Vue.createApp({
    data() {
        return {
            loading: true,
            error: null,
            rawData: {
                asef1: {},
                asef3: {},
                asef5: {}
            },
            activeTab: 'asef1',
            tabLoading: false
        }
    },
    computed: {
        // 處理 ASEF1 資料並計算統計
        processedAsef1Data() {
            const result = {};
            Object.keys(this.rawData.asef1).forEach(category => {
                const categoryData = this.rawData.asef1[category];
                const totalCount = Object.keys(categoryData).length;
                const vCount = Object.values(categoryData).filter(value => value === "V").length;
                const percentage = totalCount > 0 ? ((vCount / totalCount) * 100).toFixed(1) : 0;
                
                result[category] = {
                    raw_data: categoryData,
                    v_count: vCount,
                    total_count: totalCount,
                    percentage: parseFloat(percentage),
                    label: `${category} ${percentage}% (${vCount}/${totalCount})`
                };
            });
            return result;
        },

        // 處理 ASEF3 資料並計算統計
        processedAsef3Data() {
            const result = {};
            Object.keys(this.rawData.asef3).forEach(category => {
                const categoryData = this.rawData.asef3[category];
                const totalCount = Object.keys(categoryData).length;
                const vCount = Object.values(categoryData).filter(value => value === "V").length;
                const percentage = totalCount > 0 ? ((vCount / totalCount) * 100).toFixed(1) : 0;
                
                result[category] = {
                    raw_data: categoryData,
                    v_count: vCount,
                    total_count: totalCount,
                    percentage: parseFloat(percentage),
                    label: `${category} ${percentage}% (${vCount}/${totalCount})`
                };
            });
            return result;
        },

        // 處理 ASEF5 資料並計算統計
        processedAsef5Data() {
            const result = {};
            Object.keys(this.rawData.asef5).forEach(category => {
                const categoryData = this.rawData.asef5[category];
                const totalCount = Object.keys(categoryData).length;
                const vCount = Object.values(categoryData).filter(value => value === "V").length;
                const percentage = totalCount > 0 ? ((vCount / totalCount) * 100).toFixed(1) : 0;
                
                result[category] = {
                    raw_data: categoryData,
                    v_count: vCount,
                    total_count: totalCount,
                    percentage: parseFloat(percentage),
                    label: `${category} ${percentage}% (${vCount}/${totalCount})`
                };
            });
            return result;
        },
        
        // ASEF1 統計
        asef1Stats() {
            return this.calculateStats(this.processedAsef1Data);
        },
        
        // ASEF3 統計
        asef3Stats() {
            return this.calculateStats(this.processedAsef3Data);
        },

        // ASEF5 統計
        asef5Stats() {
            return this.calculateStats(this.processedAsef5Data);
        },

        // 當前頁籤的統計資料
        currentStats() {
            if (this.activeTab === 'asef1') return this.asef1Stats;
            if (this.activeTab === 'asef3') return this.asef3Stats;
            if (this.activeTab === 'asef5') return this.asef5Stats;
            return this.overallStats;
        },

        // 全部總計統計
        overallStats() {
            const totalCategories = this.asef1Stats.categories + this.asef3Stats.categories + this.asef5Stats.categories;
            const totalV = this.asef1Stats.vCount + this.asef3Stats.vCount + this.asef5Stats.vCount;
            const totalCount = this.asef1Stats.totalCount + this.asef3Stats.totalCount + this.asef5Stats.totalCount;
            const percentage = totalCount > 0 ? ((totalV / totalCount) * 100).toFixed(1) : 0;

            return {
                categories: totalCategories,
                vCount: totalV,
                totalCount: totalCount,
                percentage: percentage
            };
        },

        // ASEF1 總計屬性
        totalAsef1VCount() {
            return this.asef1Stats.vCount;
        },
        
        totalAsef1Count() {
            return this.asef1Stats.totalCount;
        },
        
        totalAsef1Percentage() {
            return this.asef1Stats.percentage;
        },

        // ASEF3 總計屬性
        totalAsef3VCount() {
            return this.asef3Stats.vCount;
        },
        
        totalAsef3Count() {
            return this.asef3Stats.totalCount;
        },
        
        totalAsef3Percentage() {
            return this.asef3Stats.percentage;
        },

        // ASEF5 總計屬性
        totalAsef5VCount() {
            return this.asef5Stats.vCount;
        },
        
        totalAsef5Count() {
            return this.asef5Stats.totalCount;
        },
        
        totalAsef5Percentage() {
            return this.asef5Stats.percentage;
        }
    },
    methods: {
        // 載入資料
        async loadData() {
            try {
                this.loading = true;
                this.error = null;
                const response = await fetch('http://127.0.0.1:5000/api/data');
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                if (result.error) {
                    throw new Error(result.error);
                }
                
                // 設置獲取到的數據，如果沒有 asef5 就設為空對象
                this.rawData = {
                    asef1: result.asef1 || {},
                    asef3: result.asef3 || {},
                    asef5: result.asef5 || {}
                };
                
                console.log('資料載入成功:', this.rawData);
                
            } catch (err) {
                console.error('載入資料失敗:', err);
                this.error = err.message;
            } finally {
                this.loading = false;
            }
        },
        
        // 計算統計資訊
        calculateStats(data) {
            let totalV = 0;
            let totalCount = 0;
            let categoriesCount = 0;

            Object.values(data).forEach(item => {
                if (item && item.total_count > 0) {
                    totalV += item.v_count || 0;
                    totalCount += item.total_count || 0;
                    categoriesCount++;
                }
            });

            const percentage = totalCount > 0 ? ((totalV / totalCount) * 100).toFixed(1) : 0;

            return {
                categories: categoriesCount,
                vCount: totalV,
                totalCount: totalCount,
                percentage: percentage
            };
        },

        // 根據百分比決定進度條顏色
        getProgressColorClass(percentage) {
            if (percentage <= 50) {
                return 'progress-red';
            } else if (percentage >= 51 && percentage <= 65) {
                return 'progress-yellow';
            } else if (percentage >= 66) {
                return 'progress-green';
            } else {
                return 'progress-default'; // 預設顏色
            }
        },

        // 根據百分比決定文字顏色
        getTextColorClass(percentage) {
            if (percentage <= 50) {
                return 'progress-text-white'; // 紅色背景用白色文字
            } else if (percentage >= 51 && percentage <= 65) {
                return 'progress-text-dark'; // 黃色背景用深色文字
            } else if (percentage >= 66) {
                return 'progress-text-white'; // 綠色背景用白色文字
            } else {
                return 'progress-text-white'; // 預設白色文字
            }
        },

        // 根據百分比決定統計卡片文字顏色
        getPercentageTextColor(percentage) {
            const p = parseFloat(percentage);
            if (p <= 50) {
                return 'text-red-600';
            } else if (p >= 51 && p <= 65) {
                return 'text-amber-600';
            } else {
                return 'text-green-600';
            }
        },

        // 切換頁籤（帶 loading 效果）
        switchTab(tab) {
            if (this.activeTab === tab || this.tabLoading) return;
            
            this.tabLoading = true;
            
            setTimeout(() => {
                this.activeTab = tab;
                this.tabLoading = false;
            }, 800);
        },

        // 鍵盤快捷鍵處理
        handleKeydown(e) {
            if (e.key === '1') this.switchTab('asef1');
            if (e.key === '2') this.switchTab('asef3');
            if (e.key === '3') this.switchTab('asef5');
            if (e.key === 'r' || e.key === 'R') this.loadData();
            if (e.key === 'Escape') this.goToLab();
        },

        goToEdit() {
            window.location.href = 'editMCID.html';
        },
        goToLab(){
            window.location.href = 'lab.html';
        },
    },
    
    mounted() {
        this.loadData();
        // 初始化 lucide icons（如果存在）
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
        // 綁定鍵盤事件
        window.addEventListener('keydown', this.handleKeydown.bind(this), false);
    },
    updated() {
        // 更新後重新渲染 lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    },
    beforeUnmount() {
        window.removeEventListener('keydown', this.handleKeydown, false);
    }
});

app.mount('#app');