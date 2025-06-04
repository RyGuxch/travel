// 主要前端逻辑

class TravelAgent {
    constructor() {
        this.init();
        this.checkLoginStatus();
    }

    init() {
        // 绑定事件监听器
        this.bindEvents();
        
        // 添加CSS动画类
        this.addAnimations();
    }

    // 检查登录状态
    async checkLoginStatus() {
        try {
            const response = await fetch('/api/userinfo', {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.logged_in) {
                // 用户已登录，检查是否在计划页面，只有在计划页面才加载计划
                const plansList = document.getElementById('plansList');
                if (plansList) {
                this.loadPlans();
                }
            } else {
                // 用户未登录，显示提示信息
                const plansList = document.getElementById('plansList');
                if (plansList) {
                    plansList.innerHTML = '<p class="subtitle">请先登录后查看您的旅行计划</p>';
                }
                
                // 如果URL参数要求登录，显示登录窗口
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('login_required') === '1') {
                    if (typeof showLoginModal === 'function') {
                        showLoginModal('请登录后再访问此页面');
                    }
                }
            }
        } catch (error) {
            console.error('检查登录状态失败:', error);
        }
    }

    bindEvents() {
        const planForm = document.getElementById('planForm');
        if (planForm) {
            planForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
    }

    addAnimations() {
        // 为卡片添加淡入动画
        const cards = document.querySelectorAll('.card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                
                setTimeout(() => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 100);
            }, index * 100);
        });
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        // 先检查登录状态
        try {
            const userResponse = await fetch('/api/userinfo', {
                credentials: 'include'
            });
            const userData = await userResponse.json();
            
            if (!userData.logged_in) {
                if (typeof showLoginModal === 'function') {
                    showLoginModal('请先登录后再生成旅行计划');
                } else {
                    this.showErrorMessage('请先登录后再生成旅行计划');
                }
                return;
            }
            
            // 获取表单数据
            const formData = this.getFormData();
            
            // 显示加载状态
            this.setLoading(true);
            
            // 调用API创建异步任务
            const response = await fetch('/api/generate-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                // 显示任务已提交消息
                this.showMessage('旅行方案生成中，请稍候...', 'info');
                
                // 开始轮询任务状态
                this.pollTaskStatus(result.task_id);
            } else {
                if (result.msg === '请先登录' || response.status === 401) {
                    if (typeof showLoginModal === 'function') {
                        showLoginModal('请先登录后再生成旅行计划');
                    } else {
                        this.showErrorMessage('请先登录后再生成旅行计划');
                    }
                } else {
                    this.showErrorMessage(result.error || '生成失败，请重试');
                }
                this.setLoading(false);
            }
        } catch (error) {
            console.error('Error:', error);
            this.showErrorMessage('网络错误，请检查连接后重试');
            this.setLoading(false);
        }
    }

    // 轮询任务状态
    async pollTaskStatus(taskId, interval = 3000, maxAttempts = 40) {
        let attempts = 0;
        
        // 状态消息元素
        const statusElement = document.createElement('div');
        statusElement.className = 'task-status-message';
        statusElement.innerHTML = `<div class="spinner"></div><span>正在生成您的旅行计划 (0%)...</span>`;
        document.body.appendChild(statusElement);
        
        const updateProgress = (percent) => {
            statusElement.querySelector('span').textContent = `正在生成您的旅行计划 (${percent}%)...`;
        };
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/task/${taskId}`, {
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    throw new Error('获取任务状态失败');
                }
                
                const result = await response.json();
                attempts++;
                
                // 更新进度百分比（简单模拟）
                let progressPercent = Math.min(Math.round((attempts / maxAttempts) * 80), 80);
                
                // 根据任务状态处理
                switch (result.status) {
                    case 'completed':
                        // 成功完成
                        updateProgress(100);
                        setTimeout(() => {
                            document.body.removeChild(statusElement);
                            this.showPlanResult(result.plan);
                            this.loadPlans(); // 重新加载计划列表
                            this.showSuccessMessage('旅行方案生成成功！');
                            this.setLoading(false);
                        }, 500);
                        return;
                        
                    case 'failed':
                        // 任务失败
                        document.body.removeChild(statusElement);
                        this.showErrorMessage(result.error || '生成失败，请重试');
                        this.setLoading(false);
                        return;
                        
                    case 'processing':
                        // 处理中，进度稍微更快一些
                        progressPercent = Math.min(50 + Math.round((attempts / maxAttempts) * 30), 80);
                        updateProgress(progressPercent);
                        break;
                        
                    case 'pending':
                        // 等待处理
                        updateProgress(progressPercent);
                        break;
                }
                
                // 达到最大尝试次数
                if (attempts >= maxAttempts) {
                    document.body.removeChild(statusElement);
                    this.showErrorMessage('生成超时，请稍后查看您的计划列表');
                    this.loadPlans();
                    this.setLoading(false);
                    return;
                }
                
                // 继续轮询
                setTimeout(checkStatus, interval);
                
            } catch (error) {
                console.error('轮询任务状态失败:', error);
                // 错误时继续尝试
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, interval);
                } else {
                    document.body.removeChild(statusElement);
                    this.showErrorMessage('无法获取任务状态，请稍后查看您的计划列表');
                    this.loadPlans();
                    this.setLoading(false);
                }
            }
        };
        
        // 开始轮询
        setTimeout(checkStatus, 1000);
    }

    getFormData() {
        const destinations = document.getElementById('destinations').value.split(',').map(s => s.trim()).filter(Boolean);
        const days = parseInt(document.getElementById('days').value, 10);
        const budgetMin = parseFloat(document.getElementById('budgetMin').value);
        const budgetMax = parseFloat(document.getElementById('budgetMax').value);
        const themeSel = document.getElementById('theme');
        const themeCustom = document.getElementById('themeCustom') ? document.getElementById('themeCustom').value.trim() : '';
        const theme = (themeSel.value === '自定义' && themeCustom) ? themeCustom : themeSel.value;
        const transportSel = document.getElementById('transport');
        const transportCustom = document.getElementById('transportCustom') ? document.getElementById('transportCustom').value.trim() : '';
        const transport = (transportSel.value === '自定义' && transportCustom) ? transportCustom : transportSel.value;
        const startDate = document.getElementById('startDate').value;
        return {
            destinations,
            days,
            budget_min: budgetMin,
            budget_max: budgetMax,
            theme,
            transport,
            start_date: startDate
        };
    }

    setLoading(isLoading) {
        const btnText = document.getElementById('btnText');
        const btnLoading = document.getElementById('btnLoading');
        const generateBtn = document.getElementById('generateBtn');

        if (isLoading) {
            btnText.classList.add('hidden');
            btnLoading.classList.remove('hidden');
            generateBtn.disabled = true;
        } else {
            btnText.classList.remove('hidden');
            btnLoading.classList.add('hidden');
            generateBtn.disabled = false;
        }
    }

    showPlanResult(plan) {
        const resultSection = document.getElementById('resultSection');
        const planResult = document.getElementById('planResult');

        let html = `
            <div class="plan-summary">
                <h3>${plan.title}</h3>
                <p>${plan.summary || ''}</p>
                <div class="plan-meta">
                    <span class="tag tag-primary">总费用: ¥${plan.total_cost || '待计算'}</span>
                </div>
            </div>
        `;

        if (plan.days && plan.days.length > 0) {
            html += '<div class="timeline">';
            
            plan.days.forEach(day => {
                html += `
                    <div class="timeline-item">
                        <div class="timeline-time">第${day.day}天 - ${day.date}</div>
                        <div class="timeline-title">${day.theme || '行程安排'}</div>
                        <div class="day-items">
                `;
                
                if (day.items && day.items.length > 0) {
                    day.items.forEach(item => {
                        html += `
                            <div class="item">
                                <strong>${item.time}</strong> - ${item.activity}
                                <br>
                                <small>📍 ${item.location} | 💰 ¥${item.cost || 0}</small>
                                <br>
                                <span class="item-description">${item.description || ''}</span>
                            </div>
                        `;
                    });
                }
                
                html += `
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        }

        if (plan.tips && plan.tips.length > 0) {
            html += '<div class="tips-section"><h4>实用建议：</h4><ul>';
            plan.tips.forEach(tip => {
                html += `<li>${tip}</li>`;
            });
            html += '</ul></div>';
        }

        // 添加查看详情按钮
        html += `
            <div class="plan-actions" style="margin-top: 20px; text-align: center; background: none; box-shadow: none; padding: 0;">
                <button id="viewDetailBtn" class="btn btn-primary">
                    🗺️ 查看详细地图和完整行程
                </button>
            </div>
        `;

        planResult.innerHTML = html;
        resultSection.classList.remove('hidden');
        
        // 绑定查看详情按钮事件
        const viewDetailBtn = document.getElementById('viewDetailBtn');
        if (viewDetailBtn) {
            viewDetailBtn.addEventListener('click', () => this.viewLatestPlan());
        }
        
        // 滚动到结果区域
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    viewLatestPlan() {
        // 跳转到最新创建的计划详情页
        fetch('/api/plans', {
            credentials: 'include'
        })
            .then(response => response.json())
            .then(plansData => {
                // 合并所有计划
                const allPlans = [...(plansData.future || []), ...(plansData.completed || [])];
                if (allPlans.length > 0) {
                    // 按创建时间排序，获取最新的计划
                    const latestPlan = allPlans.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];
                    window.location.href = `/plan/${latestPlan.id}`;
                } else {
                    this.showErrorMessage('暂无可查看的旅行计划');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showErrorMessage('无法跳转到详情页面');
            });
    }

    async loadPlans() {
        try {
            // 先检查是否存在计划列表元素
            const plansList = document.getElementById('plansList');
            if (!plansList) {
                console.log('计划列表元素不存在，跳过加载');
                return;
            }
            
            // 先检查登录状态
            const userResponse = await fetch('/api/userinfo', {
                credentials: 'include'
            });
            const userData = await userResponse.json();
            
            if (!userData.logged_in) {
                plansList.innerHTML = '<p class="subtitle">请先登录后查看您的旅行计划</p>';
                return;
            }
            
            const response = await fetch('/api/plans', {
                credentials: 'include'
            });
            
            // 检查响应状态
            if (response.status === 401) {
                plansList.innerHTML = '<p class="subtitle">请先登录后查看您的旅行计划</p>';
                return;
            }
            
            const plansData = await response.json();
            // 合并所有计划
            const allPlans = [...(plansData.future || []), ...(plansData.completed || [])];
            const today = new Date();
            const notStartedPlans = [];
            const ongoingPlans = [];
            const completedPlans = [];
            allPlans.forEach(plan => {
                const startDate = new Date(plan.start_date);
                const endDate = new Date(plan.end_date);
                if (endDate < today) {
                    completedPlans.push(plan);
                } else if (startDate > today) {
                    notStartedPlans.push(plan);
                } else {
                    ongoingPlans.push(plan);
                }
            });
            this.displayPlans(notStartedPlans, ongoingPlans, completedPlans);
        } catch (error) {
            console.error('Error loading plans:', error);
            const plansList = document.getElementById('plansList');
            if (plansList) {
                plansList.innerHTML = '<p class="subtitle">加载计划失败，请刷新页面重试</p>';
            }
        }
    }

    displayPlans(notStartedPlans, ongoingPlans, completedPlans) {
        const plansList = document.getElementById('plansList');
        if (!plansList) {
            console.log('计划列表元素不存在，无法显示计划');
            return;
        }
        
        let html = '';
        // 下拉切换按钮
        html += `
            <div class="plans-switch" style="margin-bottom: 18px; text-align: right;">
                <select id="plansViewSelect" class="form-input" style="width: 160px; display: inline-block;">
                    <option value="notStarted">未开始</option>
                    <option value="ongoing">进行中</option>
                    <option value="completed">已完成</option>
                </select>
            </div>
        `;
        html += this.renderPlansSection('notStarted', notStartedPlans);
        html += this.renderPlansSection('ongoing', ongoingPlans, true);
        html += this.renderPlansSection('completed', completedPlans, true);
        plansList.innerHTML = html;
        // 切换视图事件
        const select = document.getElementById('plansViewSelect');
        if (select) {
        select.addEventListener('change', function() {
                const notStartedSection = document.getElementById('plans-section-notStarted');
                const ongoingSection = document.getElementById('plans-section-ongoing');
                const completedSection = document.getElementById('plans-section-completed');
                
                if (notStartedSection) notStartedSection.style.display = select.value === 'notStarted' ? '' : 'none';
                if (ongoingSection) ongoingSection.style.display = select.value === 'ongoing' ? '' : 'none';
                if (completedSection) completedSection.style.display = select.value === 'completed' ? '' : 'none';
        });
        }
    }

    renderPlansSection(type, plans, hide = false) {
        const sectionId = `plans-section-${type}`;
        let html = `<div id="${sectionId}" style="${hide ? 'display:none;' : ''}">`;
        let title = '';
        if (type === 'notStarted') title = '未开始';
        else if (type === 'ongoing') title = '进行中';
        else if (type === 'completed') title = '已完成';
        if (!plans || plans.length === 0) {
            html += `<p class="subtitle">暂无${title}的旅行计划</p>`;
        } else {
            html += `<h3 class="title-medium">${title}</h3><div class="plans-grid">`;
            const today = new Date();
            plans.forEach(plan => {
                // 状态标签逻辑：只要end_date<今天，强制显示已完成
                let statusTag = '';
                const endDate = new Date(plan.end_date);
                if (endDate < today) {
                    statusTag = '<span class="tag tag-secondary">已完成</span>';
                } else {
                    statusTag = this.getStatusTag(plan.status);
                }
                const aiTag = plan.ai_generated ? '<span class="tag tag-primary">AI生成</span>' : '';
                html += `
                    <div class="plan-card" onclick="window.location.href='/plan/${plan.id}'">
                        <div class="plan-header">
                            <h4>${plan.title}</h4>
                            <div class="plan-tags">
                                ${statusTag}
                                ${aiTag}
                            </div>
                        </div>
                        <div class="plan-info">
                            <p>📅 ${plan.start_date} 至 ${plan.end_date}</p>
                            <p>⏱️ ${plan.total_days}天</p>
                            <p>💰 ¥${plan.budget_min} - ¥${plan.budget_max}</p>
                            <p>🎯 ${plan.travel_theme}</p>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }
        html += '</div>';
        return html;
    }

    getStatusTag(status) {
        const statusMap = {
            'draft': { class: 'tag-warning', text: '草稿' },
            'confirmed': { class: 'tag-success', text: '已确认' },
            'completed': { class: 'tag-secondary', text: '已完成' }
        };
        const statusInfo = statusMap[status] || statusMap['draft'];
        return `<span class="tag ${statusInfo.class}">${statusInfo.text}</span>`;
    }

    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }

    showErrorMessage(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        // 创建消息元素
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
            background-color: ${type === 'success' ? '#34C759' : '#FF3B30'};
        `;
        
        document.body.appendChild(messageEl);
        
        // 显示动画
        setTimeout(() => {
            messageEl.style.transform = 'translateX(0)';
        }, 10);
        
        // 自动隐藏
        setTimeout(() => {
            messageEl.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(messageEl);
            }, 300);
        }, 3000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new TravelAgent();
}); 
