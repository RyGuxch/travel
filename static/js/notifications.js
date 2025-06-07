// Web Push Notifications Manager
class NotificationManager {
    constructor() {
        this.swRegistration = null;
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.init();
    }

    async init() {
        if (!this.isSupported) {
            console.log('Push messaging is not supported');
            return;
        }

        try {
            // 注册Service Worker
            this.swRegistration = await navigator.serviceWorker.register('/static/js/sw.js');
            console.log('Service Worker registered successfully');

            // 检查当前订阅状态
            await this.checkSubscription();
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    }

    async checkSubscription() {
        if (!this.swRegistration) return;

        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            if (subscription) {
                console.log('已有推送订阅');
                // 可以在这里同步订阅状态到服务器
                await this.syncSubscriptionToServer(subscription);
            }
        } catch (error) {
            console.error('检查订阅状态失败:', error);
        }
    }

    getPermissionStatus() {
        if (!this.isSupported) return 'unsupported';
        return Notification.permission;
    }

    // 检查实际的推送订阅状态（包括服务器端）
    async getSubscriptionStatus() {
        if (!this.isSupported) return 'unsupported';
        
        const browserPermission = Notification.permission;
        if (browserPermission !== 'granted') {
            return browserPermission;
        }
        
        // 检查是否有活跃的推送订阅
        try {
            // 如果Service Worker还没有注册，先初始化
            if (!this.swRegistration) {
                await this.init();
            }
            
            // 再次检查，如果还是没有注册，说明不支持
            if (!this.swRegistration) {
                return 'no_subscription';
            }
            
            const subscription = await this.swRegistration.pushManager.getSubscription();
            if (!subscription) {
                return 'no_subscription';
            }
            
            // 检查服务器端是否有对应的订阅记录
            const response = await fetch('/api/notification-settings', {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.success && data.settings.has_subscriptions) {
                return 'granted';
            } else {
                // 浏览器有订阅但服务器没有记录，尝试同步
                await this.syncSubscriptionToServer(subscription);
                return 'granted';
            }
        } catch (error) {
            console.error('检查订阅状态失败:', error);
            return 'error';
        }
    }

    async requestPermission() {
        if (!this.isSupported) {
            throw new Error('浏览器不支持推送通知');
        }

        const permission = await Notification.requestPermission();
        return permission === 'granted';
    }

    async getVAPIDPublicKey() {
        try {
            const response = await fetch('/api/vapid-public-key', {
                credentials: 'include'
            });
            const data = await response.json();
            
            if (data.success) {
                return data.public_key;
            } else {
                throw new Error('获取VAPID公钥失败');
            }
        } catch (error) {
            console.error('获取VAPID公钥失败:', error);
            throw error;
        }
    }

    async subscribe() {
        if (!this.swRegistration) {
            throw new Error('Service Worker未注册');
        }

        try {
            // 获取VAPID公钥
            const vapidPublicKey = await this.getVAPIDPublicKey();
            
            // 创建推送订阅
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(vapidPublicKey)
            });

            // 保存订阅到服务器
            await this.saveSubscriptionToServer(subscription);
            
            console.log('推送订阅成功');
            return subscription;
        } catch (error) {
            console.error('订阅推送失败:', error);
            throw error;
        }
    }

    async unsubscribe() {
        if (!this.swRegistration) return;

        try {
            const subscription = await this.swRegistration.pushManager.getSubscription();
            if (subscription) {
                // 从服务器移除订阅
                await this.removeSubscriptionFromServer(subscription);
                
                // 取消本地订阅
                await subscription.unsubscribe();
                console.log('推送订阅已取消');
            }
        } catch (error) {
            console.error('取消订阅失败:', error);
            throw error;
        }
    }

    async saveSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/save-subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    subscription: subscription.toJSON()
                })
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.msg || '保存订阅失败');
            }
        } catch (error) {
            console.error('保存订阅到服务器失败:', error);
            throw error;
        }
    }

    async syncSubscriptionToServer(subscription) {
        // 同步现有订阅到服务器（如果服务器没有记录）
        try {
            await this.saveSubscriptionToServer(subscription);
        } catch (error) {
            console.log('同步订阅到服务器失败，可能已存在:', error);
        }
    }

    async removeSubscriptionFromServer(subscription) {
        try {
            const response = await fetch('/api/remove-subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    subscription: subscription.toJSON()
                })
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.msg || '移除订阅失败');
            }
        } catch (error) {
            console.error('从服务器移除订阅失败:', error);
            throw error;
        }
    }

    // 将VAPID公钥从base64转换为Uint8Array
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    // 显示本地通知（用于测试）
    async showLocalNotification(title, options = {}) {
        if (this.getPermissionStatus() !== 'granted') {
            throw new Error('通知权限未授予');
        }

        const notification = new Notification(title, {
            body: options.body || '这是一条测试通知',
            icon: options.icon || '/static/favicon.ico',
            badge: options.badge || '/static/favicon.ico',
            tag: options.tag || 'test-notification',
            requireInteraction: options.requireInteraction || false,
            ...options
        });

        // 点击通知时的处理
        notification.onclick = function(event) {
            event.preventDefault();
            if (options.url) {
                window.open(options.url, '_blank');
            }
            notification.close();
        };

        return notification;
    }
}

// 创建全局实例
window.notificationManager = new NotificationManager();

// 全局函数：启用通知
window.enableNotifications = async function() {
    try {
        const manager = window.notificationManager;
        
        if (!manager.isSupported) {
            throw new Error('浏览器不支持推送通知');
        }

        // 请求权限
        const granted = await manager.requestPermission();
        if (!granted) {
            throw new Error('用户拒绝了通知权限');
        }

        // 订阅推送
        await manager.subscribe();
        
        return true;
    } catch (error) {
        console.error('启用通知失败:', error);
        return false;
    }
};

// 全局函数：禁用通知
window.disableNotifications = async function() {
    try {
        const manager = window.notificationManager;
        await manager.unsubscribe();
        return true;
    } catch (error) {
        console.error('禁用通知失败:', error);
        return false;
    }
};

// 全局函数：测试通知
window.testNotification = async function() {
    try {
        const manager = window.notificationManager;
        
        if (manager.getPermissionStatus() !== 'granted') {
            const granted = await manager.requestPermission();
            if (!granted) {
                throw new Error('需要通知权限才能测试');
            }
        }

        // 显示本地测试通知
        await manager.showLocalNotification('测试通知', {
            body: '如果您看到这条通知，说明通知功能正常工作！',
            icon: '/static/favicon.ico',
            tag: 'test-notification'
        });

        return true;
    } catch (error) {
        console.error('测试通知失败:', error);
        return false;
    }
};

// 导出管理器类（如果需要）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
} 