
// ==================== User Activities Management (Admin Only) ====================
// This file handles user activity monitoring, statistics display, and user account management

// Import translations from centralized location
import { t, initializeTranslations } from '../page/translations.js';

let dailyActivityChart = null;
let eventTypeChart = null;
let currentUserActivitiesData = null;

/**
 * Get localized activity type name
 * @param {string} activityType - Activity type key
 * @returns {string} Localized name
 */
function getActivityTypeName(activityType) {
    const activityTypeNames = {
        'login_success': _('Login Success'),
        'login_failed': _('Login Failed'),
        'logout': _('Logout'),
        'register': _('Register'),
        'download_book': _('Download Book'),
        'upload_book': _('Upload Book'),
        'delete_book': _('Delete Book'),
        'search_books': _('Search Books'),
        'edit_metadata': _('Edit Metadata'),
        'push_to_kindle': _('Push to Kindle'),
        'push_to_anx': _('Push to Anx'),
        'push_anx_to_calibre': _('Push Anx to Calibre'),
        'generate_audiobook': _('Generate Audiobook'),
        'download_audiobook': _('Download Audiobook'),
        'delete_audiobook': _('Delete Audiobook'),
        'play_audiobook_update_playing_progress': _('Update Audiobook Progress'),
        'play_audiobook_update_reading_time': _('Update Audiobook Reading Time'),
        'update_reading_progress': _('Update Reading Progress'),
        'update_reading_time': _('Update Reading Time'),
        'llm_chat_start': _('Start LLM Chat'),
        'llm_chat_message': _('LLM Chat Message'),
        'llm_delete_session': _('Delete LLM Session'),
        'llm_delete_message': _('Delete LLM Message'),
        'mcp_token_generate': _('Generate MCP Token'),
        'mcp_token_delete': _('Delete MCP Token'),
        'mcp_api_call': _('MCP API Call'),
        'update_user_settings': _('Update User Settings'),
        'update_global_settings': _('Update Global Settings'),
        'update_password': _('Update Password'),
        'enable_2fa': _('Enable 2FA'),
        'disable_2fa': _('Disable 2FA'),
        'create_user': _('Create User'),
        'update_user': _('Update User'),
        'delete_user': _('Delete User'),
        'lock_user': _('Lock User'),
        'unlock_user': _('Unlock User'),
        'create_invite_code': _('Create Invite Code'),
        'delete_invite_code': _('Delete Invite Code'),
        'use_invite_code': _('Use Invite Code'),
        'toggle_invite_code': _('Toggle Invite Code'),
        'create_service_config': _('Create Service Config'),
        'update_service_config': _('Update Service Config'),
        'delete_service_config': _('Delete Service Config'),
        'test_smtp': _('Test SMTP'),
        'koreader_sync_progress': _('KOReader Sync Progress'),
        'koreader_sync_reading_time': _('KOReader Sync Reading Time'),
        'koreader_update_summary': _('KOReader Update Summary'),
        'delete_user_activity_log': _('Delete User Activity Log'),
        'delete_all_activity_logs': _('Delete All Activity Logs')
    };
    
    return activityTypeNames[activityType] || activityType;
}

/**
 * Load user activities data and display statistics
 */
window.loadUserActivities = async function() {
    if (!isAdmin) return;

    try {
        const response = await fetch('/api/admin/user-activities');
        if (response.ok) {
            const data = await response.json();
            currentUserActivitiesData = data;
            displayActivityStats(data.stats);
            displayGlobalEventStats(data.global_activity_stats);
            displayUserActivitiesList(data.users);
            await loadEventStatistics();
        } else {
            console.error('Failed to load user activities:', response.statusText);
        }
    } catch (error) {
        console.error('Error loading user activities:', error);
    }
}

/**
 * Display activity statistics summary
 * @param {Object} stats - Activity statistics data
 */
function displayActivityStats(stats) {
    const statsContainer = document.getElementById('activity-stats');
    if (!statsContainer) return;
    
    statsContainer.innerHTML = `
        <div class="stat-card">
            <h5>${t.totalUsers}</h5>
            <p class="stat-number">${stats.total_users || 0}</p>
        </div>
        <div class="stat-card">
            <h5>${t.activeToday}</h5>
            <p class="stat-number">${stats.active_today || 0}</p>
        </div>
        <div class="stat-card">
            <h5>${t.totalLogins}</h5>
            <p class="stat-number">${stats.total_logins || 0}</p>
        </div>
        <div class="stat-card">
            <h5>${t.totalActivities}</h5>
            <p class="stat-number">${stats.total_activities || 0}</p>
        </div>
    `;
}

/**
 * Display global event statistics
 * @param {Object} globalStats - Global activity statistics by event type
 */
function displayGlobalEventStats(globalStats) {
    const container = document.getElementById('global-events-stats');
    if (!container || !globalStats) return;
    
    const sortedEvents = Object.entries(globalStats)
        .sort((a, b) => b[1].total - a[1].total)
        .slice(0, 12); // 只显示前12个最常见的事件
    
    container.innerHTML = sortedEvents.map(([eventType, stats]) => `
        <div class="event-stat-card" onclick="viewEventTypeDetails('${eventType}')" style="cursor: pointer;">
            <h6>${getActivityTypeName(eventType)}</h6>
            <div class="event-stat-numbers">
                <span class="total">
                    <span class="label">${t.total}</span>
                    <span class="value">${stats.total}</span>
                </span>
                <span class="success">
                    <span class="label">${t.success}</span>
                    <span class="value">${stats.success}</span>
                </span>
                <span class="failure">
                    <span class="label">${t.failed}</span>
                    <span class="value">${stats.failure}</span>
                </span>
            </div>
        </div>
    `).join('');
}

/**
 * Load and display event statistics charts
 */
async function loadEventStatistics() {
    try {
        const response = await fetch('/api/admin/user-activities/stats/events?days=30');
        if (response.ok) {
            const data = await response.json();
            displayDailyActivityChart(data.daily_stats);
            displayEventTypeChart(data.event_stats);
        }
    } catch (error) {
        console.error('Error loading event statistics:', error);
    }
}

/**
 * Display daily activity trend chart
 * @param {Array} dailyStats - Daily activity statistics
 */
function displayDailyActivityChart(dailyStats) {
    const canvas = document.getElementById('dailyActivityChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // 销毁旧图表
    if (dailyActivityChart) {
        dailyActivityChart.destroy();
    }
    
    const labels = dailyStats.map(stat => stat.date);
    const activities = dailyStats.map(stat => stat.count);
    const uniqueUsers = dailyStats.map(stat => stat.unique_users);
    
    dailyActivityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: t.totalActivities,
                    data: activities,
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y-activities'  // 使用左侧Y轴
                },
                {
                    label: t.uniqueUsers,
                    data: uniqueUsers,
                    borderColor: 'rgb(67, 233, 123)',
                    backgroundColor: 'rgba(67, 233, 123, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y-users'  // 使用右侧Y轴
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.y;
                            return label;
                        }
                    }
                }
            },
            scales: {
                'y-activities': {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: t.totalActivities,
                        color: 'rgb(102, 126, 234)'
                    },
                    ticks: {
                        color: 'rgb(102, 126, 234)'
                    }
                },
                'y-users': {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: t.uniqueUsers,
                        color: 'rgb(67, 233, 123)'
                    },
                    ticks: {
                        color: 'rgb(67, 233, 123)'
                    },
                    grid: {
                        drawOnChartArea: false  // 不在图表区域绘制网格线，避免重叠
                    }
                }
            }
        }
    });
}

/**
 * Display event type distribution chart
 * @param {Array} eventStats - Event type statistics
 */
function displayEventTypeChart(eventStats) {
    const canvas = document.getElementById('eventTypeChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // 销毁旧图表
    if (eventTypeChart) {
        eventTypeChart.destroy();
    }
    
    // 只显示前10个最常见的事件类型
    const topEvents = eventStats.slice(0, 10);
    const labels = topEvents.map(stat => getActivityTypeName(stat.activity_type));
    const data = topEvents.map(stat => stat.total_count);
    
    // 生成颜色
    const backgroundColors = [
        'rgba(102, 126, 234, 0.8)',
        'rgba(240, 147, 251, 0.8)',
        'rgba(79, 172, 254, 0.8)',
        'rgba(67, 233, 123, 0.8)',
        'rgba(255, 193, 7, 0.8)',
        'rgba(220, 53, 69, 0.8)',
        'rgba(23, 162, 184, 0.8)',
        'rgba(108, 117, 125, 0.8)',
        'rgba(40, 167, 69, 0.8)',
        'rgba(253, 126, 20, 0.8)'
    ];
    
    eventTypeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

/**
 * Display user activities list
 * @param {Array} users - Array of user activity data
 */
function displayUserActivitiesList(users) {
    const tbody = document.querySelector('#userActivityTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    users.forEach(user => {
        const row = document.createElement('tr');
        const lastLogin = user.last_login ? formatLocalTime(user.last_login) : '-';
        const lastLoginIP = user.last_login_ip || '-';
        
        let statusHtml = '';
        if (user.is_locked) {
            const lockedUntil = formatLocalTime(user.locked_until);
            let reasonHtml = '';
            if (user.lock_reason) {
                reasonHtml = `<br><small>${t.reason}: ${user.lock_reason}</small>`;
            }
            statusHtml = `<span class="status-badge status-locked">${t.lockedUntil}: ${lockedUntil}${reasonHtml}</span>`;
        } else {
            statusHtml = `<span class="status-badge status-active">${t.active}</span>`;
        }
        
        const actionsHtml = `
            <button class="button button-small" onclick="viewUserActivityDetails(${user.id}, '${user.username}')">${t.viewDetails}</button>
            ${user.is_locked ?
                `<button class="button button-small button-success" onclick="unlockUserAccount(${user.id}, '${user.username}')">${t.unlock}</button>` :
                `<button class="button button-small button-warning" onclick="showLockUserModal(${user.id}, '${user.username}')">${t.lock}</button>`
            }
            ${user.failed_login_attempts > 0 ?
                `<button class="button button-small" onclick="resetFailedAttempts(${user.id}, '${user.username}')">${t.resetFailed}</button>` :
                ''
            }
            <button class="button button-small button-danger" onclick="deleteUserActivities(${user.id}, '${user.username}')">${t.deleteActivities}</button>
        `;
        
        row.innerHTML = `
            <td>${user.username}</td>
            <td>${user.role}</td>
            <td>${lastLogin}</td>
            <td>${lastLoginIP}</td>
            <td>${user.login_count || 0}</td>
            <td>${user.activity_count || 0}</td>
            <td>${user.failed_login_attempts || 0}</td>
            <td>${statusHtml}</td>
            <td>${actionsHtml}</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * View detailed activities for a specific user
 * @param {number} userId - User ID
 * @param {string} username - Username
 */
window.viewUserActivityDetails = async function(userId, username) {
    try {
        const response = await fetch(`/api/admin/user-activities/${username}`);
        if (response.ok) {
            const activities = await response.json();
            
            // 获取用户数据
            const userData = currentUserActivitiesData.users.find(u => u.id === userId);
            
            // 保存原始数据供筛选使用
            window.currentUserActivitiesBackup = activities;
            window.currentUsername = username;
            window.currentUserData = userData;
            
            showActivityDetailsModal(username, activities, userData);
        } else {
            alert(_('Failed to load activity details'));
        }
    } catch (error) {
        console.error('Error loading user activity details:', error);
        alert(_('Failed to load activity details'));
    }
}

/**
 * Show activity details in a modal
 * @param {string} username - Username
 * @param {Array} activities - Array of activity records
 * @param {Object} userData - User statistics data
 */
function showActivityDetailsModal(username, activities, userData) {
    const modal = document.getElementById('activityDetailsModal');
    const modalUserName = document.getElementById('modalUserName');
    const contentDiv = document.getElementById('activityDetailsContent');
    
    if (!modal || !modalUserName || !contentDiv) return;
    
    modalUserName.textContent = _('Activity Details for') + ': ' + username;
    
    // 显示用户统计
    document.getElementById('userTotalActivities').textContent = userData.activity_count || 0;
    document.getElementById('userLoginCount').textContent = userData.login_count || 0;
    document.getElementById('userLastLogin').textContent = userData.last_login ?
        formatLocalTime(userData.last_login) : '-';
    
    // 显示最后活动时间
    displayLastActivities(userData.last_activities);
    
    // 显示失败登录历史
    displayFailedLogins(userData.last_failed_login);
    
    // 重置筛选下拉框
    const filterSelect = document.getElementById('activityTypeFilter');
    if (filterSelect) {
        filterSelect.value = '';
    }
    
    // 显示活动历史表格
    let html = '<table class="data-table"><thead><tr>';
    html += `<th>${t.time}</th>`;
    html += `<th>${t.activityType}</th>`;
    html += `<th>${t.status}</th>`;
    html += `<th>${t.details}</th>`;
    html += '</tr></thead><tbody>';
    
    if (activities.length === 0) {
        html += `<tr><td colspan="4" style="text-align: center;">${t.noActivitiesFound}</td></tr>`;
    } else {
        activities.forEach(activity => {
            const time = formatLocalTime(activity.timestamp);
            const statusIcon = activity.success ? '✓' : '✗';
            const statusClass = activity.success ? 'success' : 'failure';
            const details = activity.failure_reason || activity.detail || activity.book_title || '-';
            
            html += `<tr>`;
            html += `<td>${time}</td>`;
            html += `<td>${getActivityTypeName(activity.activity_type)}</td>`;
            html += `<td><span class="${statusClass}">${statusIcon}</span></td>`;
            html += `<td>${details}</td>`;
            html += `</tr>`;
        });
    }
    
    html += '</tbody></table>';
    contentDiv.innerHTML = html;
    modal.style.display = 'block';
}

/**
 * Display last activities by type
 * @param {Object} lastActivities - Last activity times by type
 */
function displayLastActivities(lastActivities) {
    const container = document.getElementById('lastActivitiesGrid');
    if (!container) return;
    
    const activityTypeNames = {
        'download_book': _('Download Book'),
        'upload_book': _('Upload Book'),
        'search_books': _('Search Books'),
        'update_reading_progress': _('Reading Progress'),
        'push_to_kindle': _('Push to Kindle'),
        'generate_audiobook': _('Generate Audiobook')
    };
    
    if (Object.keys(lastActivities).length === 0) {
        container.innerHTML = `<p>${t.noRecentActivities}</p>`;
        return;
    }
    
    container.innerHTML = Object.entries(lastActivities).map(([type, time]) => `
        <div class="last-activity-item">
            <div class="activity-type">${activityTypeNames[type] || type}</div>
            <div class="activity-time">${formatLocalTime(time)}</div>
        </div>
    `).join('');
}

/**
 * Display failed login attempts
 * @param {Object} failedLogin - Last failed login data
 */
function displayFailedLogins(failedLogin) {
    const container = document.getElementById('failedLoginsContainer');
    if (!container) return;
    
    if (!failedLogin) {
        container.innerHTML = `<div class="no-failed-logins">${t.noFailedLoginAttempts}</div>`;
        return;
    }
    
    container.innerHTML = `
        <div class="failed-login-item">
            <div class="time">${formatLocalTime(failedLogin.created_at)}</div>
            <div class="details">
                ${t.ip}: ${failedLogin.ip_address || '-'}<br>
                ${t.reason}: ${failedLogin.failure_reason || '-'}
            </div>
        </div>
    `;
}

/**
 * Close the activity details modal
 */
window.closeActivityModal = function() {
    const modal = document.getElementById('activityDetailsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * View detailed activities for a specific event type
 * @param {string} eventType - Event type to view details for
 */
window.viewEventTypeDetails = async function(eventType) {
    try {
        const response = await fetch(`/api/admin/user-activities/by-type/${eventType}`);
        if (response.ok) {
            const activities = await response.json();
            showEventTypeDetailsModal(eventType, activities);
        } else {
            alert(_('Failed to load event type details'));
        }
    } catch (error) {
        console.error('Error loading event type details:', error);
        alert(_('Failed to load event type details'));
    }
}

/**
 * Show event type details in a modal
 * @param {string} eventType - Event type
 * @param {Array} activities - Array of activity records
 */
function showEventTypeDetailsModal(eventType, activities) {
    const modal = document.getElementById('eventTypeDetailsModal');
    const modalTitle = document.getElementById('eventTypeModalTitle');
    const contentDiv = document.getElementById('eventTypeDetailsContent');
    
    if (!modal || !modalTitle || !contentDiv) return;
    
    modalTitle.textContent = _('Activity Details for') + ': ' + getActivityTypeName(eventType);
    
    let html = '<table class="data-table"><thead><tr>';
    html += `<th>${t.time}</th>`;
    html += `<th>${t.user}</th>`;
    html += `<th>${t.status}</th>`;
    html += `<th>${t.details}</th>`;
    html += '</tr></thead><tbody>';
    
    activities.forEach(activity => {
        const time = formatLocalTime(activity.timestamp);
        const statusIcon = activity.success ? '✓' : '✗';
        const statusClass = activity.success ? 'success' : 'failure';
        const details = activity.failure_reason || activity.detail || activity.book_title || '-';
        
        html += `<tr>`;
        html += `<td>${time}</td>`;
        html += `<td>${activity.username}</td>`;
        html += `<td><span class="${statusClass}">${statusIcon}</span></td>`;
        html += `<td>${details}</td>`;
        html += `</tr>`;
    });
    
    html += '</tbody></table>';
    contentDiv.innerHTML = html;
    modal.style.display = 'block';
}

/**
 * Close the event type details modal
 */
window.closeEventTypeModal = function() {
    const modal = document.getElementById('eventTypeDetailsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Filter user activities
 */
window.filterUserActivities = function() {
    const activityType = document.getElementById('activityTypeFilter').value;
    
    if (!window.currentUserActivities || !window.currentUsername) {
        return;
    }
    
    // 筛选活动
    let filteredActivities = window.currentUserActivitiesBackup;
    if (activityType) {
        filteredActivities = window.currentUserActivitiesBackup.filter(act =>
            act.activity_type === activityType
        );
    }
    
    // 重新显示模态框内容
    showActivityDetailsModal(window.currentUsername, filteredActivities, window.currentUserData);
}

/**
 * Refresh user activities
 */
window.refreshUserActivities = async function() {
    await loadUserActivities();
}

/**
 * Show lock user modal
 * @param {number} userId - User ID
 * @param {string} username - Username
 */
window.showLockUserModal = function(userId, username) {
    const modal = document.getElementById('lockUserModal');
    if (!modal) return;
    
    document.getElementById('lockUserId').value = userId;
    document.getElementById('lockUserName').value = username;
    document.getElementById('lockDuration').value = 30;
    document.getElementById('lockReason').value = '';
    document.getElementById('lockPermanent').checked = false;
    document.getElementById('lockDuration').disabled = false;
    document.getElementById('lockModalTitle').textContent = _('Lock User Account') + ' - ' + username;
    
    modal.style.display = 'block';
}

/**
 * Close lock user modal
 */
window.closeLockModal = function() {
    const modal = document.getElementById('lockUserModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Confirm lock user
 */
window.togglePermanentLock = function(checkbox) {
    const durationInput = document.getElementById('lockDuration');
    durationInput.disabled = checkbox.checked;
}

window.confirmLockUser = async function() {
    const userId = document.getElementById('lockUserId').value;
    const isPermanent = document.getElementById('lockPermanent').checked;
    let duration = parseInt(document.getElementById('lockDuration').value);
    const reason = document.getElementById('lockReason').value;

    if (isPermanent) {
        duration = 0; // 0 or negative for permanent lock
    } else if (!duration || duration < 1) {
        alert(_('Please enter a valid duration'));
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/lock`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                duration_minutes: duration,
                reason: reason || _('Locked by administrator')
            })
        });
        
        if (response.ok) {
            alert(_('User account locked successfully'));
            closeLockModal();
            await loadUserActivities();
        } else {
            const data = await response.json();
            alert(_('Failed to lock user account') + ': ' + (data.error || ''));
        }
    } catch (error) {
        console.error('Error locking user:', error);
        alert(_('Failed to lock user account'));
    }
}

/**
 * Unlock user account
 * @param {number} userId - User ID
 * @param {string} username - Username
 */
window.unlockUserAccount = async function(userId, username) {
    if (!confirm(_('Are you sure you want to unlock this user account?') + '\n' + username)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/unlock`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            alert(_('User account unlocked successfully'));
            await loadUserActivities();
        } else {
            const data = await response.json();
            alert(_('Failed to unlock user account') + ': ' + (data.error || ''));
        }
    } catch (error) {
        console.error('Error unlocking user:', error);
        alert(_('Failed to unlock user account'));
    }
}

/**
 * Reset failed login attempts
 * @param {number} userId - User ID
 * @param {string} username - Username
 */
window.resetFailedAttempts = async function(userId, username) {
    if (!confirm(_('Are you sure you want to reset failed login attempts for this user?') + '\n' + username)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/users/${userId}/reset-failed-attempts`, {
            method: 'POST',
headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            alert(_('Failed login attempts reset successfully'));
            await loadUserActivities();
        } else {
            const data = await response.json();
            alert(_('Failed to reset login attempts') + ': ' + (data.error || ''));
        }
    } catch (error) {
        console.error('Error resetting failed attempts:', error);
        alert(_('Failed to reset login attempts'));
    }
}

// Search functionality
const userSearchInput = document.getElementById('userSearchInput');
if (userSearchInput) {
    userSearchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#userActivityTable tbody tr');
        
        rows.forEach(row => {
            const username = row.cells[0].textContent.toLowerCase();
            if (username.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

// Initialize user activities when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize translations first
    await initializeTranslations();
    
    if (isAdmin) {
        await loadUserActivities();
    }
});

/**
 * Delete all activities for a specific user
 * @param {number} userId - User ID
 * @param {string} username - Username
 */
window.deleteUserActivities = async function(userId, username) {
    if (!confirm(t.areYouSureDeleteUserActivities.replace('%s', username))) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/users/${userId}/activities`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();
            alert(data.message || t.deleteUserActivitiesSuccess.replace('%s', username));
            await loadUserActivities();
        } else {
            const data = await response.json();
            alert(t.deleteActivitiesError + ': ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting user activities:', error);
        alert(t.deleteActivitiesError);
    }
}

/**
 * Delete all activities for all users
 */
window.deleteAllActivities = async function() {
    if (!confirm(t.areYouSureDeleteAllActivities)) {
        return;
    }

    try {
        const response = await fetch('/api/admin/user-activities/all', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();
            alert(data.message || t.deleteAllActivitiesSuccess);
            await loadUserActivities();
        } else {
            const data = await response.json();
            alert(t.deleteAllActivitiesError + ': ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting all activities:', error);
        alert(t.deleteAllActivitiesError);
    }
}