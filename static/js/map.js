// 地图相关功能

class TravelMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.map = null;
        this.markers = [];
        this.polylines = [];
        this.routeCache = null; // 路线缓存
        this.routeVisible = false; // 路线显示状态
        this.currentWaypointsHash = null; // 当前路径点哈希
        this.options = {
            zoom: 12,
            center: [116.397428, 39.90923], // 默认北京
            ...options
        };
        this.initMap();
    }

    initMap() {
        // 检查高德地图API是否已加载
        if (typeof AMap === 'undefined') {
            console.error('高德地图API未加载，请检查API密钥配置');
            const container = document.getElementById(this.containerId);
            if (container) {
                container.innerHTML = `
                    <div style="padding: 40px; text-align: center; color: #666;">
                        <h3>地图加载失败</h3>
                        <p>高德地图API未正确加载</p>
                        <p>请检查API密钥配置</p>
                        <small>当前需要配置 AMAP_WEB_KEY 环境变量</small>
                    </div>
                `;
            }
            return;
        }

        // 初始化高德地图
        this.map = new AMap.Map(this.containerId, {
            zoom: this.options.zoom,
            center: this.options.center,
            viewMode: '3D',
            lang: 'zh_cn',
            features: ['bg', 'road', 'building', 'point'],
            mapStyle: 'amap://styles/normal'
        });

        // 添加地图控件
        this.addControls();
        
        // 添加地图事件监听
        this.bindEvents();
    }

    addControls() {
        try {
            // 缩放控件
            this.map.addControl(new AMap.Scale());
            
            // 工具栏控件
            this.map.addControl(new AMap.ToolBar({
                position: {
                    top: '110px',
                    right: '20px'
                }
            }));
            
            console.log('地图控件添加成功');
        } catch (error) {
            console.error('添加地图控件失败:', error);
        }
    }

    bindEvents() {
        // 地图点击事件
        this.map.on('click', (e) => {
            console.log('地图点击坐标:', e.lnglat.getLng(), e.lnglat.getLat());
        });
    }

    // 添加标记点
    addMarker(options) {
        const {
            position,
            title = '',
            content = '',
            icon = null,
            animation = 'drop'
        } = options;

        const markerOptions = {
            position: position,
            title: title
        };

        // 设置动画
        if (AMap.Animation && AMap.Animation.AMAP_ANIMATION_DROP) {
            markerOptions.animation = AMap.Animation.AMAP_ANIMATION_DROP;
        } else {
            // 使用字符串值作为备选
            markerOptions.animation = animation;
        }

        // 自定义图标
        if (icon) {
            markerOptions.icon = new AMap.Icon({
                size: new AMap.Size(32, 32),
                image: icon,
                imageSize: new AMap.Size(32, 32)
            });
        }

        const marker = new AMap.Marker(markerOptions);
        
        // 添加信息窗口
        if (content) {
            const infoWindow = new AMap.InfoWindow({
                content: content,
                offset: new AMap.Pixel(0, -30)
            });

            marker.on('click', () => {
                infoWindow.open(this.map, marker.getPosition());
            });
        }

        this.map.add(marker);
        this.markers.push(marker);
        
        return marker;
    }

    // 添加多个标记点
    addMarkers(markersData) {
        markersData.forEach(markerData => {
            this.addMarker(markerData);
        });
    }

    // 计算路径点哈希值，用于判断路径是否改变
    calculateWaypointsHash(waypoints) {
        if (!waypoints || waypoints.length === 0) return null;
        
        // 将所有坐标点转换为字符串并排序（保持一致性）
        const coordStrings = waypoints.map(point => `${point[0].toFixed(6)},${point[1].toFixed(6)}`);
        const hashString = coordStrings.join('|');
        
        // 简单哈希函数
        let hash = 0;
        for (let i = 0; i < hashString.length; i++) {
            const char = hashString.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 转换为32位整数
        }
        return hash.toString();
    }

    // 绘制路线（带缓存优化）
    drawRoute(waypoints, options = {}) {
        const {
            strokeColor = '#FF6B6B',
            strokeWeight = 6,
            strokeOpacity = 0.8,
            forceRefresh = false // 强制刷新标志
        } = options;

        // 验证输入参数
        if (!waypoints || waypoints.length < 2) {
            console.warn('路线规划需要至少2个坐标点');
            return;
        }

        // 过滤无效坐标
        const validWaypoints = waypoints.filter(point => {
            return Array.isArray(point) && 
                   point.length === 2 && 
                   typeof point[0] === 'number' && 
                   typeof point[1] === 'number' &&
                   point[0] >= -180 && point[0] <= 180 &&
                   point[1] >= -90 && point[1] <= 90;
        });

        if (validWaypoints.length < 2) {
            console.warn('有效坐标点不足2个');
            return;
        }

        // 限制中间点数量并进行抽样
        let processedWaypoints = validWaypoints;
        if (validWaypoints.length > 8) {
            processedWaypoints = this.sampleWaypoints(validWaypoints, 6);
            console.log(`坐标点过多，抽样为${processedWaypoints.length}个点`);
        }

        // 计算当前路径的哈希值
        const waypointsHash = this.calculateWaypointsHash(processedWaypoints);
        
        // 检查是否需要重新计算路线
        if (!forceRefresh && 
            this.routeCache && 
            this.currentWaypointsHash === waypointsHash) {
            console.log('使用缓存的路线数据');
            this.showCachedRoute(options);
            return;
        }

        // 清除旧路线
        this.clearRoutes();
        
        // 更新当前路径哈希
        this.currentWaypointsHash = waypointsHash;
        
        console.log('计算新路线（路径已改变或首次计算）');
        
        // 调用后端路线规划API
        this.planRouteViaAPI(processedWaypoints, options);
    }

    // 通过后端API进行路线规划
    async planRouteViaAPI(waypoints, options = {}) {
        try {
            console.log(`调用后端路线规划API: ${waypoints.length}个坐标点`);
            
            const response = await fetch('/api/route-planning', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    waypoints: waypoints
                })
            });

            const result = await response.json();

            if (result.success && result.route) {
                console.log('后端路线规划成功');
                
                // 保存路线数据到缓存
                this.routeCache = {
                    routeData: result.route,
                    originalWaypoints: waypoints,
                    timestamp: Date.now()
                };
                
                this.drawRouteFromAPI(result.route, options);
                this.showRouteInfo(result.route, waypoints, false);
                this.routeVisible = true;
                
                console.log('路线数据已缓存');
            } else {
                console.error('后端路线规划失败:', result.error);
                this.handleRouteError(result.error || '路线规划失败');
            }
        } catch (error) {
            console.error('调用路线规划API失败:', error);
            this.handleRouteError('网络错误，无法获取路线信息');
        }
    }

    // 根据API返回的路线数据绘制路线
    drawRouteFromAPI(routeData, options = {}) {
        const {
            strokeColor = '#007AFF',
            strokeWeight = 5,
            strokeOpacity = 0.8
        } = options;

        if (!routeData.polyline || routeData.polyline.length === 0) {
            console.warn('路线数据为空');
            return;
        }

        // 创建路线
        const polyline = new AMap.Polyline({
            path: routeData.polyline,
            strokeColor: strokeColor,
            strokeWeight: strokeWeight,
            strokeOpacity: strokeOpacity,
            lineJoin: 'round',
            lineCap: 'round'
        });

        this.map.add(polyline);
        this.polylines.push(polyline);

        console.log(`路线绘制完成: ${routeData.distance}公里, ${routeData.duration}分钟`);
    }

    // 处理路线规划错误
    handleRouteError(errorMessage) {
        console.warn('路线规划失败:', errorMessage);
        
        // 显示错误信息
        const routeInfoEl = document.getElementById('routeInfo');
        if (routeInfoEl) {
            routeInfoEl.innerHTML = `
                <div class="route-error">
                    <span style="color: #FF3B30;">⚠️ ${errorMessage}</span>
                </div>
            `;
        }

        // 可以触发消息提示
        if (this.showMessage) {
            this.showMessage(errorMessage, 'warning');
        }
    }

    // 抽样航点，保留起点、终点和关键中间点
    sampleWaypoints(waypoints, maxPoints) {
        if (waypoints.length <= maxPoints) {
            return waypoints;
        }

        const result = [waypoints[0]]; // 起点
        const step = Math.floor((waypoints.length - 2) / (maxPoints - 2));
        
        for (let i = step; i < waypoints.length - 1; i += step) {
            if (result.length < maxPoints - 1) {
                result.push(waypoints[i]);
            }
        }
        
        result.push(waypoints[waypoints.length - 1]); // 终点
        return result;
    }

    // 计算两点间距离（米）
    calculateDistance(point1, point2) {
        if (!point1 || !point2) return Infinity;
        
        const R = 6371000; // 地球半径（米）
        const dLat = (point2[1] - point1[1]) * Math.PI / 180;
        const dLon = (point2[0] - point1[0]) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(point1[1] * Math.PI / 180) * Math.cos(point2[1] * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    showRouteInfo(routeData, originalWaypoints, isFromCache = false) {
        // 显示路线信息
        const routeInfoEl = document.getElementById('routeInfo');
        if (routeInfoEl) {
            const statusText = isFromCache ? '缓存' : '最新';
            const statusClass = isFromCache ? 'route-cached' : 'route-fresh';
            
            routeInfoEl.innerHTML = `
                <div class="route-info">
                    <span class="route-distance">🚗 距离: ${routeData.distance}公里</span>
                    <span class="route-duration">⏱️ 时间: ${routeData.duration}分钟</span>
                    <span class="route-points">📍 途经: ${routeData.waypoints_count}个地点</span>
                    <span class="route-status ${statusClass}">✨ ${statusText}</span>
                </div>
            `;
        }

        // 更新页面统计信息中的总距离
        const totalDistanceEl = document.getElementById('totalDistance');
        if (totalDistanceEl) {
            totalDistanceEl.textContent = `${routeData.distance}公里`;
        }
    }

    // 清除路线
    clearRoutes() {
        this.polylines.forEach(polyline => {
            this.map.remove(polyline);
        });
        this.polylines = [];
    }

    // 清除标记
    clearMarkers() {
        this.markers.forEach(marker => {
            this.map.remove(marker);
        });
        this.markers = [];
    }

    // 适应所有标记点
    fitView() {
        if (this.markers.length > 0) {
            this.map.setFitView(this.markers);
        }
    }

    // 设置地图中心
    setCenter(position, zoom = null) {
        this.map.setCenter(position);
        if (zoom) {
            this.map.setZoom(zoom);
        }
    }

    // 根据行程数据显示地图
    showItinerary(itineraryData) {
        // 清除之前的标记和路线
        this.clearMarkers();
        this.clearRoutes();
        
        // 清理路线缓存（因为行程数据已改变）
        this.clearRouteCache();

        const allPositions = [];
        const uniqueWaypoints = [];
        const seenCoordinates = new Set();

        // 遍历每日行程
        itineraryData.itineraries.forEach((itinerary, dayIndex) => {
            itinerary.items.forEach((item, itemIndex) => {
                if (item.latitude && item.longitude) {
                    const position = [item.longitude, item.latitude];
                    allPositions.push(position);

                    // 检查坐标是否重复（保留2位小数精度）
                    const coordKey = `${item.longitude.toFixed(4)},${item.latitude.toFixed(4)}`;
                    if (!seenCoordinates.has(coordKey)) {
                        seenCoordinates.add(coordKey);
                        uniqueWaypoints.push(position);
                    }

                    // 创建标记内容
                    const content = `
                        <div class="marker-info">
                            <h4>${item.title}</h4>
                            <p class="time">🕐 ${item.start_time}</p>
                            <p class="location">📍 ${item.location}</p>
                            <p class="description">${item.description || ''}</p>
                            ${item.estimated_cost ? `<p class="cost">💰 ¥${item.estimated_cost}</p>` : ''}
                        </div>
                    `;

                    // 添加标记
                    this.addMarker({
                        position: position,
                        title: item.title,
                        content: content,
                        icon: this.getActivityIcon(item.activity_type)
                    });
                }
            });
        });

        // 适应视图
        if (allPositions.length > 0) {
            this.fitView();
        }
        
        console.log(`行程数据已更新，共${uniqueWaypoints.length}个不重复地点`);
    }

    // 清理路线缓存
    clearRouteCache() {
        this.routeCache = null;
        this.currentWaypointsHash = null;
        this.routeVisible = false;
        console.log('路线缓存已清理');
    }

    // 根据活动类型获取图标
    getActivityIcon(activityType) {
        // 暂时不使用自定义图标，返回null使用默认标记
        return null;
    }

    // 搜索地点
    searchPlace(keyword, callback) {
        const placeSearch = new AMap.PlaceSearch({
            pageSize: 10,
            pageIndex: 1
        });

        placeSearch.search(keyword, (status, result) => {
            if (status === 'complete') {
                callback(result.poiList.pois);
            } else {
                callback([]);
            }
        });
    }

    // 获取当前位置
    getCurrentLocation(callback) {
        this.map.plugin('AMap.Geolocation', () => {
            const geolocation = new AMap.Geolocation({
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0,
                convert: true,
                showButton: true,
                buttonPosition: 'LT',
                buttonOffset: new AMap.Pixel(10, 20),
                showMarker: true,
                showCircle: true,
                panToLocation: true,
                zoomToAccuracy: true
            });

            geolocation.getCurrentPosition((status, result) => {
                if (status === 'complete') {
                    callback(result.position);
                } else {
                    console.error('获取位置失败:', result.message);
                    callback(null);
                }
            });
        });
    }

    // 销毁地图
    destroy() {
        if (this.map) {
            this.map.destroy();
        }
    }

    // 显示缓存的路线
    showCachedRoute(options = {}) {
        if (!this.routeCache) {
            console.warn('没有缓存的路线数据');
            return;
        }

        // 清除当前路线
        this.clearRoutes();
        
        // 重新绘制缓存的路线
        this.drawRouteFromAPI(this.routeCache.routeData, options);
        this.showRouteInfo(this.routeCache.routeData, this.routeCache.originalWaypoints, true);
        
        this.routeVisible = true;
    }

    // 隐藏路线但保留缓存
    hideRoute() {
        this.clearRoutes();
        this.routeVisible = false;
        
        // 清除路线信息显示
        const routeInfoEl = document.getElementById('routeInfo');
        if (routeInfoEl) {
            routeInfoEl.innerHTML = '';
        }
    }

    // 检查是否有可显示的缓存路线
    hasCachedRoute() {
        return this.routeCache !== null && this.currentWaypointsHash !== null;
    }

    // 获取缓存信息（调试用）
    getCacheInfo() {
        if (!this.routeCache) {
            return { status: 'no_cache' };
        }
        
        return {
            status: 'cached',
            waypoints_count: this.routeCache.routeData.waypoints_count,
            distance: this.routeCache.routeData.distance,
            duration: this.routeCache.routeData.duration,
            cached_at: new Date(this.routeCache.timestamp).toLocaleString(),
            hash: this.currentWaypointsHash,
            visible: this.routeVisible
        };
    }

    // 打印缓存状态到控制台（调试用）
    debugCacheStatus() {
        console.log('=== 路线缓存状态 ===');
        console.log(this.getCacheInfo());
        console.log('==================');
    }
}

// 地图工具函数
class MapUtils {
    // 地理编码
    static async geocode(address) {
        try {
            const response = await fetch(`/api/geocode?address=${encodeURIComponent(address)}`, {
                credentials: 'include'
            });
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('地理编码失败:', error);
            return null;
        }
    }

    // 计算两点间距离
    static calculateDistance(pos1, pos2) {
        return AMap.GeometryUtil.distance(pos1, pos2);
    }

    // 格式化距离
    static formatDistance(distance) {
        if (distance < 1000) {
            return Math.round(distance) + 'm';
        } else {
            return (distance / 1000).toFixed(1) + 'km';
        }
    }
}

// 导出类
window.TravelMap = TravelMap;
window.MapUtils = MapUtils; 
