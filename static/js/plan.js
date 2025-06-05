// 计划详情页面功能

class PlanDetailPage {
    constructor() {
        this.planId = window.PLAN_ID || null;
        this.map = null;
        this.planData = null;
        this.init();
    }

    async init() {
        if (!this.planId) {
            console.error('计划ID未找到');
            return;
        }

        // 显示加载状态
        this.showLoading(true);

        try {
            // 先检查登录状态
            const userResponse = await fetch('/api/userinfo', {
                credentials: 'include'
            });
            const userData = await userResponse.json();
            
            if (!userData.logged_in) {
                // 如果页面有showLoginModal函数，则显示登录窗口
                if (typeof window.showLoginModal === 'function') {
                    window.showLoginModal('请登录后查看旅行计划');
                }
                this.showLoading(false);
                return;
            }
            
            // 加载计划数据
            await this.loadPlanData();
            
            // 初始化地图
            this.initMap();
            
            // 渲染行程时间线
            this.renderItinerary();
            
            // 计算统计信息
            this.calculateStats();
            
            // 初始化状态显示
            this.updateStatusDisplay();
            
            // 绑定事件
            this.bindEvents();
            
        } catch (error) {
            console.error('初始化失败:', error);
            this.showError('加载计划数据失败，请刷新页面重试');
        } finally {
            this.showLoading(false);
        }
    }

    async loadPlanData() {
        const response = await fetch(`/api/plan/${this.planId}`, {
            credentials: 'include'
        });
        if (!response.ok) {
            throw new Error('获取计划数据失败');
        }
        this.planData = await response.json();
    }

    initMap() {
        // 检查高德地图API是否已加载
        if (typeof AMap === 'undefined') {
            console.warn('高德地图API未加载，地图功能将不可用');
            const mapContainer = document.getElementById('mapContainer');
            if (mapContainer) {
                mapContainer.innerHTML = `
                    <div style="padding: 40px; text-align: center; color: #666; background-color: #f5f5f5; border-radius: 8px;">
                        <h3>🗺️ 地图功能暂不可用</h3>
                        <p>高德地图API未正确加载</p>
                        <p>请检查网络连接或配置有效的API密钥</p>
                        <small>配置方法：在环境变量中设置 AMAP_WEB_KEY</small>
                    </div>
                `;
            }
            
            // 通知用户
            this.showMessage('地图功能不可用，可能是API密钥未配置或网络问题', 'warning');
            
            return;
        }

        try {
            // 初始化地图
            this.map = new TravelMap('mapContainer', {
                zoom: 12,
                center: [116.397428, 39.90923]
            });

            // 显示行程数据
            if (this.planData) {
                this.map.showItinerary(this.planData);
            }
        } catch (error) {
            console.error('地图初始化失败:', error);
            const mapContainer = document.getElementById('mapContainer');
            if (mapContainer) {
                mapContainer.innerHTML = `
                    <div style="padding: 40px; text-align: center; color: #666; background-color: #f5f5f5; border-radius: 8px;">
                        <h3>🗺️ 地图加载出错</h3>
                        <p>初始化地图时发生错误</p>
                        <p>详细错误: ${error.message || '未知错误'}</p>
                    </div>
                `;
            }
            this.showMessage('地图加载失败，请刷新页面重试', 'error');
        }
    }

    renderItinerary() {
        const timeline = document.getElementById('itineraryTimeline');
        if (!this.planData || !this.planData.itineraries) {
            timeline.innerHTML = '<p>暂无行程数据</p>';
            return;
        }

        let html = '';
        
        this.planData.itineraries.forEach(itinerary => {
            html += `
                <div class="timeline-day" data-day="${itinerary.day_number}">
                    <div class="timeline-header">
                        <div class="day-number">第${itinerary.day_number}天</div>
                        <div class="day-date">${this.formatDate(itinerary.date)}</div>
                        ${itinerary.theme ? `<div class="day-theme">${itinerary.theme}</div>` : ''}
                    </div>
                    <div class="timeline-items">
            `;

            if (itinerary.items && itinerary.items.length > 0) {
                itinerary.items.forEach(item => {
                    const activityIcon = this.getActivityIcon(item.activity_type);
                    html += `
                        <div class="timeline-item" data-lat="${item.latitude}" data-lng="${item.longitude}">
                            <div class="item-time">${item.start_time}${item.end_time ? ' - ' + item.end_time : ''}</div>
                            <div class="item-content">
                                <div class="item-header">
                                    <span class="activity-icon">${activityIcon}</span>
                                    <h4 class="item-title">${item.title}</h4>
                                    ${item.estimated_cost ? `<span class="item-cost">¥${item.estimated_cost}</span>` : ''}
                                </div>
                                ${item.location ? `<p class="item-location">📍 ${item.location}</p>` : ''}
                                ${item.description ? `<p class="item-description">${item.description}</p>` : ''}
                            </div>
                            <div class="item-actions">
                                <button class="btn-icon" onclick="planDetail.focusOnMap(${item.latitude}, ${item.longitude})" title="在地图上查看">
                                    🗺️
                                </button>
                            </div>
                        </div>
                    `;
                });
            } else {
                html += '<div class="no-items">该日暂无安排</div>';
            }

            html += `
                    </div>
                    ${itinerary.notes ? `<div class="day-notes">${itinerary.notes}</div>` : ''}
                </div>
            `;
        });

        timeline.innerHTML = html;
    }

    calculateStats() {
        if (!this.planData || !this.planData.itineraries) return;

        let totalCost = 0;
        let totalLocations = 0;
        let locationSet = new Set();

        this.planData.itineraries.forEach(itinerary => {
            if (itinerary.items) {
                itinerary.items.forEach(item => {
                    if (item.estimated_cost) {
                        totalCost += parseFloat(item.estimated_cost);
                    }
                    if (item.location) {
                        locationSet.add(item.location);
                    }
                });
            }
        });

        totalLocations = locationSet.size;
        const avgDailyCost = totalCost / this.planData.total_days;

        // 更新统计显示
        document.getElementById('totalCost').textContent = `¥${totalCost.toFixed(0)}`;
        document.getElementById('totalLocations').textContent = totalLocations;
        document.getElementById('avgDailyCost').textContent = `¥${avgDailyCost.toFixed(0)}`;
        
        // 距离统计需要地图路线计算完成后更新
        document.getElementById('totalDistance').textContent = '计算中...';
    }

    bindEvents() {
        // 显示路线按钮
        const showRouteBtn = document.getElementById('showRouteBtn');
        if (showRouteBtn) {
            showRouteBtn.addEventListener('click', () => {
                this.toggleRoute();
            });
        }

        // 刷新路线按钮
        const refreshRouteBtn = document.getElementById('refreshRouteBtn');
        if (refreshRouteBtn) {
            refreshRouteBtn.addEventListener('click', () => {
                this.forceRefreshRoute();
            });
        }

        // 适应视图按钮
        const fitViewBtn = document.getElementById('fitViewBtn');
        if (fitViewBtn) {
            fitViewBtn.addEventListener('click', () => {
                if (!this.map) {
                    this.showMessage('地图功能不可用', 'warning');
                    return;
                }
                this.map.fitView();
            });
        }

        // 分享按钮
        const shareBtn = document.getElementById('shareBtn');
        if (shareBtn) {
            shareBtn.addEventListener('click', () => {
                this.sharePlan();
            });
        }

        // 编辑按钮
        const editBtn = document.getElementById('editBtn');
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                this.editPlan();
            });
        }

        // 打印按钮
        const printBtn = document.getElementById('printBtn');
        if (printBtn) {
            printBtn.addEventListener('click', () => {
                this.printPlan();
            });
        }

        // 删除按钮
        const deleteBtn = document.getElementById('deleteBtn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                this.deletePlan();
            });
        }

        // 时间线项目点击事件
        document.addEventListener('click', (e) => {
            const timelineItem = e.target.closest('.timeline-item');
            if (timelineItem) {
                const lat = timelineItem.getAttribute('data-lat');
                const lng = timelineItem.getAttribute('data-lng');
                if (lat && lng) {
                    this.focusOnMap(parseFloat(lat), parseFloat(lng));
                }
            }
        });
    }

    toggleRoute() {
        // 切换路线显示
        const btn = document.getElementById('showRouteBtn');
        if (!this.map) {
            this.showMessage('地图功能不可用，无法显示路线', 'warning');
            return;
        }

        // 检查是否有缓存的路线
        if (this.map.hasCachedRoute()) {
            // 有缓存路线，切换显示/隐藏状态
            if (this.map.routeVisible) {
                // 当前路线可见，隐藏路线
                this.map.hideRoute();
                btn.textContent = '显示路线';
                console.log('路线已隐藏（缓存保留）');
            } else {
                // 当前路线隐藏，显示缓存路线
                this.map.showCachedRoute();
                btn.textContent = '隐藏路线';
                console.log('显示缓存的路线');
            }
        } else {
            // 没有缓存路线，需要首次计算
            if (btn.textContent === '显示路线') {
                this.showRoute();
                btn.textContent = '隐藏路线';
            } else {
                this.hideRoute();
                btn.textContent = '显示路线';
            }
        }
    }

    // 强制刷新路线（重新计算）
    forceRefreshRoute() {
        if (!this.map) {
            this.showMessage('地图功能不可用', 'warning');
            return;
        }

        console.log('强制刷新路线');
        this.showRoute(true); // 传入强制刷新标志
        
        const btn = document.getElementById('showRouteBtn');
        if (btn) {
            btn.textContent = '隐藏路线';
        }
    }

    showRoute(forceRefresh = false) {
        if (!this.map) {
            this.showMessage('地图功能不可用', 'warning');
            return;
        }
        
        if (this.planData) {
            // 提取所有有坐标的点
            const waypoints = [];
            const seenCoordinates = new Set();
            
            this.planData.itineraries.forEach(itinerary => {
                if (itinerary.items) {
                    itinerary.items.forEach(item => {
                        if (item.latitude && item.longitude) {
                            // 检查坐标是否重复（保留4位小数精度）
                            const coordKey = `${item.longitude.toFixed(4)},${item.latitude.toFixed(4)}`;
                            if (!seenCoordinates.has(coordKey)) {
                                seenCoordinates.add(coordKey);
                                waypoints.push([item.longitude, item.latitude]);
                            }
                        }
                    });
                }
            });

            console.log(`收集到${waypoints.length}个不重复坐标点`);

            if (waypoints.length > 1) {
                // 使用地图对象的路线规划方法（已经更新为使用后端API）
                this.map.drawRoute(waypoints, { forceRefresh });
                
                if (forceRefresh) {
                    this.showMessage(`强制重新规划包含${waypoints.length}个地点的路线...`, 'info');
                } else {
                    this.showMessage(`正在规划包含${waypoints.length}个地点的路线...`, 'info');
                }
            } else {
                this.showMessage('没有足够的坐标点来绘制路线', 'info');
            }
        }
    }

    hideRoute() {
        if (this.map) {
            this.map.hideRoute();
        }
    }

    focusOnMap(lat, lng) {
        if (!this.map) {
            this.showMessage('地图功能不可用，无法定位', 'warning');
            return;
        }
        
        if (lat && lng) {
            this.map.setCenter([lng, lat], 15);
        }
    }

    sharePlan() {
        // 分享计划功能
        const url = window.location.href;
        if (navigator.share) {
            navigator.share({
                title: this.planData.title,
                text: `查看我的旅行计划：${this.planData.title}`,
                url: url
            });
        } else {
            // 复制链接到剪贴板
            navigator.clipboard.writeText(url).then(() => {
                this.showMessage('链接已复制到剪贴板', 'success');
            }).catch(() => {
                // 如果复制失败，显示链接
                prompt('复制下面的链接分享:', url);
            });
        }
    }

    editPlan() {
        // 检查是否有权限编辑
        if (this.planData.status !== 'draft') {
            if (!confirm('该计划已确认，确定要编辑吗？这将使计划回到草稿状态。')) {
                return;
            }
        }
        
        // 创建编辑模态框
        const modal = document.createElement('div');
        modal.id = 'editPlanModal';
        modal.className = 'modal';
        
        // 生成行程编辑HTML
        let daysHtml = '';
        this.planData.itineraries.forEach(day => {
            let itemsHtml = '';
            
            // 为每个行程项生成编辑表单
            if (day.items && day.items.length > 0) {
                day.items.forEach((item, itemIndex) => {
                    itemsHtml += `
                    <div class="edit-item" data-item-index="${itemIndex}">
                        <div class="item-header">
                            <h4>行程项 #${itemIndex + 1}</h4>
                            <button type="button" class="btn-icon delete-item" onclick="planDetail.removeItineraryItem(${day.day_number}, ${itemIndex})">🗑️</button>
                        </div>
                        <div class="form-group">
                            <label>标题</label>
                            <input type="text" class="form-input item-title" value="${item.title || ''}" placeholder="活动名称">
                        </div>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>开始时间</label>
                                <input type="text" class="form-input item-start-time" value="${item.start_time || ''}" placeholder="如：09:00 或 09：00" pattern="[0-9]{1,2}[：:][0-9]{2}" title="请输入时间格式，如 09:00">
                            </div>
                            <div class="form-group">
                                <label>结束时间</label>
                                <input type="text" class="form-input item-end-time" value="${item.end_time || ''}" placeholder="如：17:00 或 17：00" pattern="[0-9]{1,2}[：:][0-9]{2}" title="请输入时间格式，如 17:00">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>地点</label>
                            <input type="text" class="form-input item-location" value="${item.location || ''}" placeholder="地点名称">
                        </div>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>经度</label>
                                <input type="number" step="0.000001" class="form-input item-longitude" value="${item.longitude || ''}" placeholder="经度">
                            </div>
                            <div class="form-group">
                                <label>纬度</label>
                                <input type="number" step="0.000001" class="form-input item-latitude" value="${item.latitude || ''}" placeholder="纬度">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>活动类型</label>
                            <select class="form-input item-activity-type">
                                <option value="visit" ${item.activity_type === 'visit' ? 'selected' : ''}>参观景点</option>
                                <option value="meal" ${item.activity_type === 'meal' ? 'selected' : ''}>用餐</option>
                                <option value="transport" ${item.activity_type === 'transport' ? 'selected' : ''}>交通</option>
                                <option value="rest" ${item.activity_type === 'rest' ? 'selected' : ''}>休息/住宿</option>
                                <option value="shopping" ${item.activity_type === 'shopping' ? 'selected' : ''}>购物</option>
                                <option value="entertainment" ${item.activity_type === 'entertainment' ? 'selected' : ''}>娱乐</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>估计花费 (¥)</label>
                            <input type="number" class="form-input item-cost" value="${item.estimated_cost || ''}" placeholder="预计花费">
                        </div>
                        <div class="form-group">
                            <label>描述</label>
                            <textarea class="form-input item-description" placeholder="详细描述">${item.description || ''}</textarea>
                        </div>
                        <div class="form-group">
                            <button type="button" class="btn btn-small btn-secondary map-search-btn" 
                                onclick="planDetail.searchLocationOnMap(${day.day_number}, ${itemIndex})">
                                🔍 地图搜索地点
                            </button>
                        </div>
                        <hr style="margin: 16px 0; border: none; border-top: 1px dashed #eee;">
                    </div>
                    `;
                });
            } else {
                itemsHtml = '<p>该日暂无行程项</p>';
            }
            
            daysHtml += `
            <div class="edit-day" data-day="${day.day_number}">
                <div class="day-header">
                    <h3>第${day.day_number}天 (${this.formatDate(day.date)})</h3>
                </div>
                <div class="day-items">${itemsHtml}</div>
                <div class="day-actions">
                    <button type="button" class="btn btn-small btn-outline" onclick="planDetail.addItineraryItem(${day.day_number})">
                        + 添加行程项
                    </button>
                </div>
            </div>
            `;
        });
        
        // 完整的编辑模态框内容
        modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>编辑旅行计划</h2>
                <button type="button" class="btn-close" onclick="planDetail.closeEditModal()">×</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>计划标题</label>
                    <input type="text" id="editPlanTitle" class="form-input" value="${this.planData.title || ''}">
                </div>
                <div class="grid-2">
                    <div class="form-group">
                        <label>出行主题</label>
                        <input type="text" id="editTravelTheme" class="form-input" value="${this.planData.travel_theme || ''}">
                    </div>
                    <div class="form-group">
                        <label>出行方式</label>
                        <input type="text" id="editTransportMode" class="form-input" value="${this.planData.transport_mode || ''}">
                    </div>
                </div>
                <div class="grid-2">
                    <div class="form-group">
                        <label>预算下限 (¥)</label>
                        <input type="number" id="editBudgetMin" class="form-input" value="${this.planData.budget_min || ''}">
                    </div>
                    <div class="form-group">
                        <label>预算上限 (¥)</label>
                        <input type="number" id="editBudgetMax" class="form-input" value="${this.planData.budget_max || ''}">
                    </div>
                </div>
                <div class="grid-2">
                    <div class="form-group">
                        <label>开始日期</label>
                        <input type="date" id="editStartDate" class="form-input" value="${this.planData.start_date || ''}">
                    </div>
                    <div class="form-group">
                        <label>结束日期</label>
                        <input type="date" id="editEndDate" class="form-input" value="${this.planData.end_date || ''}">
                    </div>
                </div>
                
                <h3 style="margin-top: 20px;">行程详情</h3>
                <div id="editItinerary" class="edit-itinerary">
                    ${daysHtml}
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="planDetail.closeEditModal()">取消</button>
                <button type="button" class="btn btn-primary" onclick="planDetail.savePlan()">保存计划</button>
            </div>
        </div>
        `;
        
        document.body.appendChild(modal);
    }

    // 搜索地点并填充坐标
    searchLocationOnMap(dayNumber, itemIndex) {
        const dayElement = document.querySelector(`.edit-day[data-day="${dayNumber}"]`);
        if (!dayElement) return;
        
        const itemElement = dayElement.querySelectorAll('.edit-item')[itemIndex];
        if (!itemElement) return;
        
        const locationInput = itemElement.querySelector('.item-location');
        const location = locationInput.value.trim();
        
        if (!location) {
            this.showMessage('请先输入地点名称', 'warning');
            return;
        }
        
        this.showMessage(`正在搜索地点: ${location}...`, 'info');
        
        // 调用地图API搜索地点
        fetch(`/api/geocode?address=${encodeURIComponent(location)}`, {
            credentials: 'include'
        }).then(res => res.json())
        .then(data => {
            console.log('地理编码结果:', data);
            if (data.latitude && data.longitude) {
                // 填充经纬度
                itemElement.querySelector('.item-longitude').value = data.longitude;
                itemElement.querySelector('.item-latitude').value = data.latitude;
                
                this.showMessage(`已找到地点并更新坐标: ${data.formatted_address || location}`, 'success');
                
                // 在地图上预览
                if (this.map) {
                    this.map.setCenter([data.longitude, data.latitude], 15);
                    
                    // 临时标记
                    const marker = new AMap.Marker({
                        position: [data.longitude, data.latitude],
                        animation: 'AMAP_ANIMATION_DROP',
                        title: location
                    });
                    
                    this.map.map.add(marker);
                    
                    // 3秒后移除临时标记
                    setTimeout(() => {
                        this.map.map.remove(marker);
                    }, 3000);
                }
            } else {
                this.showMessage(`未找到地点: ${location}`, 'error');
            }
        })
        .catch(err => {
            console.error('搜索地点出错:', err);
            this.showMessage('搜索地点时出错', 'error');
        });
    }

    // 关闭编辑模态框
    closeEditModal() {
        const modal = document.getElementById('editPlanModal');
        if (modal) document.body.removeChild(modal);
    }

    // 添加行程项
    addItineraryItem(dayNumber) {
        const dayElement = document.querySelector(`.edit-day[data-day="${dayNumber}"]`);
        if (!dayElement) return;
        
        const dayItems = dayElement.querySelector('.day-items');
        const itemsCount = dayElement.querySelectorAll('.edit-item').length;
        
        const newItem = document.createElement('div');
        newItem.className = 'edit-item';
        newItem.dataset.itemIndex = itemsCount;
        
        newItem.innerHTML = `
        <div class="item-header">
            <h4>行程项 #${itemsCount + 1}</h4>
            <button type="button" class="btn-icon delete-item" onclick="planDetail.removeItineraryItem(${dayNumber}, ${itemsCount})">🗑️</button>
        </div>
        <div class="form-group">
            <label>标题</label>
            <input type="text" class="form-input item-title" placeholder="活动名称">
        </div>
        <div class="grid-2">
            <div class="form-group">
                <label>开始时间</label>
                <input type="text" class="form-input item-start-time" placeholder="如：09:00 或 09：00" pattern="[0-9]{1,2}[：:][0-9]{2}" title="请输入时间格式，如 09:00">
            </div>
            <div class="form-group">
                <label>结束时间</label>
                <input type="text" class="form-input item-end-time" placeholder="如：17:00 或 17：00" pattern="[0-9]{1,2}[：:][0-9]{2}" title="请输入时间格式，如 17:00">
            </div>
        </div>
        <div class="form-group">
            <label>地点</label>
            <input type="text" class="form-input item-location" placeholder="地点名称">
        </div>
        <div class="grid-2">
            <div class="form-group">
                <label>经度</label>
                <input type="number" step="0.000001" class="form-input item-longitude" placeholder="经度">
            </div>
            <div class="form-group">
                <label>纬度</label>
                <input type="number" step="0.000001" class="form-input item-latitude" placeholder="纬度">
            </div>
        </div>
        <div class="form-group">
            <label>活动类型</label>
            <select class="form-input item-activity-type">
                <option value="visit">参观景点</option>
                <option value="meal">用餐</option>
                <option value="transport">交通</option>
                <option value="rest">休息/住宿</option>
                <option value="shopping">购物</option>
                <option value="entertainment">娱乐</option>
            </select>
        </div>
        <div class="form-group">
            <label>估计花费 (¥)</label>
            <input type="number" class="form-input item-cost" placeholder="预计花费">
        </div>
        <div class="form-group">
            <label>描述</label>
            <textarea class="form-input item-description" placeholder="详细描述"></textarea>
        </div>
        <div class="form-group">
            <button type="button" class="btn btn-small btn-secondary map-search-btn" 
                onclick="planDetail.searchLocationOnMap(${dayNumber}, ${itemsCount})">
                🔍 地图搜索地点
            </button>
        </div>
        <hr style="margin: 16px 0; border: none; border-top: 1px dashed #eee;">
        `;
        
        dayItems.appendChild(newItem);
    }

    // 删除行程项
    removeItineraryItem(dayNumber, itemIndex) {
        const dayElement = document.querySelector(`.edit-day[data-day="${dayNumber}"]`);
        if (!dayElement) return;
        
        const items = dayElement.querySelectorAll('.edit-item');
        if (itemIndex >= 0 && itemIndex < items.length) {
            items[itemIndex].remove();
            
            // 更新剩余项的索引
            dayElement.querySelectorAll('.edit-item').forEach((item, idx) => {
                item.dataset.itemIndex = idx;
                item.querySelector('h4').textContent = `行程项 #${idx + 1}`;
                
                // 更新删除按钮的onclick参数
                const deleteBtn = item.querySelector('.delete-item');
                deleteBtn.setAttribute('onclick', `planDetail.removeItineraryItem(${dayNumber}, ${idx})`);
                
                // 更新地图搜索按钮的onclick参数
                const searchBtn = item.querySelector('.map-search-btn');
                searchBtn.setAttribute('onclick', `planDetail.searchLocationOnMap(${dayNumber}, ${idx})`);
            });
        }
    }

    // 保存计划
    async savePlan() {
        try {
            this.showLoading(true);
            
            // 收集计划基本信息
            const updatedPlan = {
                title: document.getElementById('editPlanTitle').value.trim(),
                travel_theme: document.getElementById('editTravelTheme').value.trim(),
                transport_mode: document.getElementById('editTransportMode').value.trim(),
                budget_min: parseInt(document.getElementById('editBudgetMin').value) || 0,
                budget_max: parseInt(document.getElementById('editBudgetMax').value) || 0,
                start_date: document.getElementById('editStartDate').value,
                end_date: document.getElementById('editEndDate').value,
                status: 'draft',
                itineraries: []
            };
            
            // 校验必填项
            if (!updatedPlan.title) {
                this.showMessage('请输入计划标题', 'warning');
                this.showLoading(false);
                return;
            }
            
            // 收集每天的行程数据
            const dayElements = document.querySelectorAll('.edit-day');
            dayElements.forEach(dayElement => {
                const dayNumber = parseInt(dayElement.dataset.day);
                
                // 从原始数据中找到对应天的数据
                const originalDay = this.planData.itineraries.find(i => i.day_number === dayNumber);
                if (!originalDay) return;
                
                const updatedItems = [];
                
                // 收集每个行程项的数据
                const itemElements = dayElement.querySelectorAll('.edit-item');
                itemElements.forEach(itemElement => {
                    // 获取并处理时间字段，将中文冒号转换为英文冒号
                    let startTime = itemElement.querySelector('.item-start-time').value.trim();
                    let endTime = itemElement.querySelector('.item-end-time').value.trim();
                    
                    // 替换中文冒号为英文冒号
                    if (startTime) {
                        startTime = startTime.replace(/：/g, ':');
                    }
                    if (endTime) {
                        endTime = endTime.replace(/：/g, ':');
                    }
                    
                    const updatedItem = {
                        title: itemElement.querySelector('.item-title').value.trim(),
                        start_time: startTime,
                        end_time: endTime,
                        location: itemElement.querySelector('.item-location').value.trim(),
                        longitude: parseFloat(itemElement.querySelector('.item-longitude').value) || null,
                        latitude: parseFloat(itemElement.querySelector('.item-latitude').value) || null,
                        activity_type: itemElement.querySelector('.item-activity-type').value,
                        estimated_cost: parseInt(itemElement.querySelector('.item-cost').value) || 0,
                        description: itemElement.querySelector('.item-description').value.trim()
                    };
                    
                    // 校验必填项
                    if (updatedItem.title) {
                        updatedItems.push(updatedItem);
                    }
                });
                
                updatedPlan.itineraries.push({
                    day_number: dayNumber,
                    date: originalDay.date,
                    items: updatedItems
                });
            });
            
            console.log('提交更新的计划数据:', JSON.stringify(updatedPlan));
            
            // 发送更新请求
            const response = await fetch(`/api/plan/${this.planId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(updatedPlan)
            });
            
            // 检查响应状态码
            if (!response.ok) {
                const errorText = await response.text();
                console.error('保存计划响应错误:', response.status, errorText);
                throw new Error(`服务器响应错误: ${response.status} ${errorText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('计划更新成功', 'success');
                this.closeEditModal();
                
                // 重新加载计划数据
                await this.loadPlanData();
                
                // 更新地图和界面
                this.initMap();
                this.renderItinerary();
                this.calculateStats();
                
                // 立即更新状态显示
                this.updateStatusDisplay();
            } else {
                this.showError(result.msg || '保存失败');
            }
        } catch (error) {
            console.error('保存计划时出错:', error);
            this.showError(`保存计划时出错: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    // 更新状态显示
    updateStatusDisplay() {
        if (!this.planData) return;
        
        // 查找状态徽章元素
        const statusBadge = document.querySelector('.status-badge');
        if (statusBadge) {
            // 移除旧的状态类
            statusBadge.classList.remove('status-draft', 'status-confirmed', 'status-completed');
            // 添加新的状态类
            statusBadge.classList.add(`status-${this.planData.status}`);
            
            // 更新状态文本
            let statusText = '';
            switch(this.planData.status) {
                case 'draft': statusText = '草稿'; break;
                case 'confirmed': statusText = '已确认'; break;
                case 'completed': statusText = '已完成'; break;
                default: statusText = this.planData.status;
            }
            statusBadge.textContent = statusText;
        }
        
        // 更新确认按钮显示
        const confirmBtnContainer = document.querySelector('.status-badge').parentNode;
        const existingBtn = document.getElementById('confirmPlanBtn');
        
        if (this.planData.status === 'draft') {
            // 如果是草稿状态但没有确认按钮，添加一个
            if (!existingBtn) {
                const confirmBtn = document.createElement('button');
                confirmBtn.id = 'confirmPlanBtn';
                confirmBtn.className = 'btn btn-small btn-success';
                confirmBtn.style.marginLeft = '12px';
                confirmBtn.textContent = '确认计划';
                confirmBtn.addEventListener('click', function() {
                    this.disabled = true;
                    this.textContent = '正在确认...';
                    fetch(`/api/plan/${window.PLAN_ID}/confirm`, {method: 'POST'})
                        .then(res => res.json())
                        .then(data => {
                            if (data.success) {
                                location.reload();
                            } else {
                                alert(data.message || '确认失败');
                                this.disabled = false;
                                this.textContent = '确认计划';
                            }
                        })
                        .catch(() => {
                            alert('网络错误，确认失败');
                            this.disabled = false;
                            this.textContent = '确认计划';
                        });
                });
                confirmBtnContainer.appendChild(confirmBtn);
            }
        } else {
            // 如果不是草稿状态但有确认按钮，移除它
            if (existingBtn) {
                existingBtn.remove();
            }
        }
    }

    printPlan() {
        // 打印计划功能
        window.print();
    }

    getActivityIcon(activityType) {
        const iconMap = {
            'visit': '🏛️',
            'meal': '🍽️',
            'transport': '🚗',
            'rest': '🏨',
            'shopping': '🛍️',
            'entertainment': '🎭'
        };
        return iconMap[activityType] || '📍';
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
        const month = date.getMonth() + 1;
        const day = date.getDate();
        const weekday = days[date.getDay()];
        return `${month}月${day}日 ${weekday}`;
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    showMessage(message, type = 'info') {
        // 显示消息提示
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            z-index: 10000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;

        // 设置背景色
        const colorMap = {
            'success': '#34C759',
            'error': '#FF3B30',
            'warning': '#FF9500',
            'info': '#007AFF'
        };
        messageEl.style.backgroundColor = colorMap[type] || colorMap.info;

        document.body.appendChild(messageEl);

        // 显示动画
        setTimeout(() => {
            messageEl.style.transform = 'translateX(0)';
        }, 10);

        // 自动隐藏
        setTimeout(() => {
            messageEl.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (document.body.contains(messageEl)) {
                    document.body.removeChild(messageEl);
                }
            }, 300);
        }, 3000);
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    async deletePlan() {
        if (!confirm('确定要删除此旅行计划吗？此操作不可恢复。')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/plan/${this.planId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            // 检查响应的内容类型
            const contentType = response.headers.get('content-type');
            
            if (response.ok) {
                // 成功响应
                if (contentType && contentType.includes('application/json')) {
                    const data = await response.json();
                    this.showMessage(data.msg || '旅行计划已删除', 'success');
                } else {
                this.showMessage('旅行计划已删除', 'success');
                }
                
                // 跳转到计划列表页
                setTimeout(() => {
                    window.location.href = '/plans';
                }, 1500);
            } else {
                // 错误响应
                let errorMessage = '删除失败';
                
                if (contentType && contentType.includes('application/json')) {
                    try {
                const data = await response.json();
                        errorMessage = data.msg || data.message || `删除失败 (${response.status})`;
                    } catch (jsonError) {
                        console.error('解析错误响应JSON失败:', jsonError);
                        errorMessage = `删除失败 (${response.status})`;
                    }
                } else {
                    // 如果不是JSON响应（可能是HTML错误页面）
                    errorMessage = `删除失败 (${response.status}: ${response.statusText})`;
                }
                
                this.showError(errorMessage);
            }
        } catch (error) {
            console.error('删除计划时出错:', error);
            this.showError('网络错误，请重试');
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    window.planDetail = new PlanDetailPage();
}); 
