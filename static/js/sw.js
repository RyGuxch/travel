// Service Worker for Web Push Notifications
const CACHE_NAME = 'travel-agent-v1';

// Install Service Worker
self.addEventListener('install', event => {
    console.log('Service Worker installing...');
    self.skipWaiting();
});

// Activate Service Worker
self.addEventListener('activate', event => {
    console.log('Service Worker activating...');
    event.waitUntil(clients.claim());
});

// Handle Push Messages
self.addEventListener('push', event => {
    console.log('Push message received:', event);
    
    if (!event.data) {
        console.log('Push event but no data');
        return;
    }

    try {
        const data = event.data.json();
        console.log('Push data:', data);
        
        const options = {
            body: data.body || '你收到了一条新消息',
            icon: '/static/favicon.ico',
            badge: '/static/favicon.ico',
            tag: 'message-notification',
            requireInteraction: true,
            actions: [
                {
                    action: 'view',
                    title: '查看消息'
                },
                {
                    action: 'close',
                    title: '关闭'
                }
            ],
            data: {
                url: data.url || '/friends',
                sender: data.sender,
                messageId: data.messageId
            }
        };

        event.waitUntil(
            self.registration.showNotification(data.title || '新消息', options)
        );
    } catch (error) {
        console.error('Error handling push:', error);
        // Fallback notification
        event.waitUntil(
            self.registration.showNotification('新消息', {
                body: '你收到了一条新消息',
                icon: '/static/favicon.ico'
            })
        );
    }
});

// Handle Notification Click
self.addEventListener('notificationclick', event => {
    console.log('Notification clicked:', event);
    
    event.notification.close();
    
    if (event.action === 'close') {
        return;
    }
    
    const urlToOpen = event.notification.data?.url || '/friends';
    
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then(clientList => {
            // 检查是否已有窗口打开
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    client.navigate(urlToOpen);
                    return client.focus();
                }
            }
            
            // 如果没有窗口打开，打开新窗口
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// Handle Background Sync (for offline message sending)
self.addEventListener('sync', event => {
    if (event.tag === 'message-sync') {
        event.waitUntil(syncMessages());
    }
});

// Sync offline messages
async function syncMessages() {
    // This would handle sending messages that were queued while offline
    console.log('Syncing offline messages...');
} 