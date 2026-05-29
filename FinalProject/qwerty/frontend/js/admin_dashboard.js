// ============== Real Data from API ==============
let sellers = [];
let riders = [];
let orders = [];
let selectedSellerForReview = null;
let currentRiderFilter = 'all';

// Fallback authFetch if not loaded from script.js
if (typeof authFetch !== 'function') {
    async function authFetch(url, options = {}) {
        const token = localStorage.getItem('hub_access_token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return fetch(url, { ...options, headers });
    }
}

// ============== Data Loading ==============
window.loadDashboardData = async function loadDashboardData() {
    try {
        const response = await authFetch('/api/admin/dashboard');
        if (!response.ok) throw new Error('Failed to load dashboard');
        
        const data = await response.json();
        if (data.success && data.data) {
            const dash = data.data;
            
            // Update main metrics
            document.getElementById('salesToday').textContent = '₱' + (dash.sales_today || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
            document.getElementById('salesTodayCount').textContent = (dash.sales_today_count || 0) + ' orders';
            document.getElementById('salesMonth').textContent = '₱' + (dash.sales_month || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
            document.getElementById('salesMonthCount').textContent = (dash.sales_month_count || 0) + ' orders';
            document.getElementById('pendingOrders').textContent = dash.pending_orders || 0;
            document.getElementById('avgRating').textContent = (dash.avg_rating || 0).toFixed(1);
            document.getElementById('totalSellers').textContent = dash.total_sellers || 0;
            document.getElementById('totalRiders').textContent = dash.total_riders || 0;
            document.getElementById('pendingSellersCount').textContent = (dash.pending_sellers || 0) + ' pending';
            document.getElementById('pendingRidersCount').textContent = (dash.pending_riders || 0) + ' pending';
            
            // Update sidebar badges
            const pendingSellersBadge = document.getElementById('pendingSellersBadge');
            if (pendingSellersBadge) {
                const pendingCount = dash.pending_sellers || 0;
                pendingSellersBadge.textContent = pendingCount;
                pendingSellersBadge.style.display = pendingCount > 0 ? 'inline-block' : 'none';
            }
            
            const pendingRidersBadge = document.getElementById('pendingRidersBadge');
            if (pendingRidersBadge) {
                const pendingCount = dash.pending_riders || 0;
                pendingRidersBadge.textContent = pendingCount;
                pendingRidersBadge.style.display = pendingCount > 0 ? 'inline-block' : 'none';
            }
            
            // Legacy fields for compatibility
            if (document.getElementById('totalOrders')) {
                document.getElementById('totalOrders').textContent = dash.total_orders || 0;
            }
            if (document.getElementById('activeOrders')) {
                document.getElementById('activeOrders').textContent = dash.active_orders || 0;
            }
            if (document.getElementById('completedOrders')) {
                document.getElementById('completedOrders').textContent = dash.completed_orders || 0;
            }
            if (document.getElementById('totalUsers')) {
                document.getElementById('totalUsers').textContent = dash.total_users || 0;
            }
            if (document.getElementById('platformRevenue')) {
                document.getElementById('platformRevenue').textContent = '₱' + (dash.total_revenue || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
            }
        }
        
        // Load widgets in parallel
        await Promise.all([
            loadTopProducts(),
            loadRecentActivities(),
            loadRevenueTrend(),
            loadOrderGrowth(),
            loadUserGrowth(),
            loadApprovalBreakdown()
        ]);

        // Update store counts after lists are fetched (use API stats)
        // Store counts removed - single store per seller
    } catch (err) {
        console.error('Dashboard data error:', err);
    }
}
// Store filter buttons removed - single store per seller


// Store management removed - single store per seller (no multi-store functionality)

async function loadTopProducts() {
    try {
        const response = await authFetch('/api/admin/top-products?limit=5');
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.success && data.data) {
            renderTopProducts(data.data);
        }
    } catch (err) {
        console.error('Top products error:', err);
    }
}

function renderTopProducts(products) {
    const tbody = document.getElementById('topProductsTable');
    if (!tbody) return;
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:20px;color:#999;">No sales data yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = products.map(p => `
        <tr>
            <td>
                <div style="display:flex;align-items:center;gap:8px;">
                    ${p.img_url ? `<img src="${p.img_url}" style="width:32px;height:32px;border-radius:4px;object-fit:cover;">` : ''}
                    <div>
                        <strong>${p.title}</strong><br>
                        <small style="color:#999;">${p.category || 'N/A'}</small>
                    </div>
                </div>
            </td>
            <td><small style="color:#666;">${p.seller_name || 'Unknown'}</small></td>
            <td style="text-align:right;">
                <strong>${p.total_sold || 0}</strong> sold<br>
                <small style="color:#28a745;">₱${(p.total_revenue || 0).toLocaleString('en-PH', {minimumFractionDigits:2})}</small>
            </td>
        </tr>
    `).join('');
}

async function loadRecentActivities() {
    try {
        const response = await authFetch('/api/admin/recent-activities?limit=10');
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.success && data.data) {
            renderRecentActivities(data.data);
        }
    } catch (err) {
        console.error('Recent activities error:', err);
    }
}

function renderRecentActivities(activities) {
    const container = document.getElementById('activityLog');
    if (!container) return;
    
    if (!activities || activities.length === 0) {
        container.innerHTML = '<p style="text-align:center;padding:20px;color:#999;">No recent activity</p>';
        return;
    }
    
    container.innerHTML = activities.map(activity => {
        const timeAgo = getTimeAgo(activity.created_at);
        let icon, message, subtitle;
        
        if (activity.activity_type === 'order') {
            icon = 'fa-cart-shopping';
            const statusClass = getStatusClass(activity.status);
            message = `<strong>${activity.customer_name || 'Customer'}</strong> placed order #${activity.id}`;
            subtitle = `${timeAgo} • ₱${(activity.total || 0).toLocaleString('en-PH', {minimumFractionDigits:2})} <span class="status-badge ${statusClass}" style="margin-left:8px;font-size:11px;padding:2px 6px;border-radius:3px;">${activity.status}</span>`;
        } else if (activity.activity_type === 'review') {
            icon = 'fa-star';
            const stars = '★'.repeat(activity.rating || 0) + '☆'.repeat(5 - (activity.rating || 0));
            message = `<strong>${activity.customer_name || 'Customer'}</strong> reviewed "${activity.product_name || 'Product'}"`;
            subtitle = `${timeAgo} • ${stars} ${activity.rating || 0}/5`;
        } else if (activity.activity_type === 'registration') {
            icon = 'fa-user-plus';
            const roleLabels = { 'customer': 'Customer', 'seller': 'Seller', 'rider': 'Rider', 'admin': 'Admin' };
            message = `<strong>${activity.customer_name || 'User'}</strong> registered as ${roleLabels[activity.role] || activity.role}`;
            subtitle = timeAgo;
        } else {
            icon = 'fa-circle';
            message = `Activity from ${activity.customer_name || 'User'}`;
            subtitle = timeAgo;
        }
        
        return `
            <div class="activity-item" style="padding:12px;border-bottom:1px solid #eee;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="width:32px;height:32px;border-radius:50%;background:#f0f0f0;display:flex;align-items:center;justify-content:center;">
                        <i class="fas ${icon}" style="font-size:14px;color:#666;"></i>
                    </span>
                    <div style="flex:1;">
                        <p style="margin:0;font-size:14px;">${message}</p>
                        <small style="color:#999;">${subtitle}</small>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function getTimeAgo(dateString) {
    if (!dateString) return 'recently';
    const now = new Date();
    const past = new Date(dateString);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return past.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getStatusClass(status) {
    const statusMap = {
        'pending': 'status-pending',
        'processing': 'status-processing',
        'dispatched': 'status-dispatched',
        'delivered': 'status-approved',
        'completed': 'status-approved',
        'cancelled': 'status-rejected'
    };
    return statusMap[status?.toLowerCase()] || 'status-pending';
}

let adminRevenueTrendChart = null;
async function loadRevenueTrend() {
    try {
        const response = await authFetch('/api/admin/revenue-trend?period=30');
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.success && data.data) {
            renderRevenueTrendChart(data.data);
        }
    } catch (err) {
        console.error('Revenue trend error:', err);
    }
}

function renderRevenueTrendChart(trendData) {
    const canvas = document.getElementById('revenueTrendChart');
    if (!canvas) return;
    
    if (adminRevenueTrendChart) {
        adminRevenueTrendChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    const labels = trendData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const revenues = trendData.map(d => d.revenue);
    
    adminRevenueTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue',
                data: revenues,
                borderColor: '#4caf50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '₱' + context.parsed.y.toLocaleString('en-PH', {minimumFractionDigits: 2});
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₱' + value.toLocaleString('en-PH');
                        }
                    }
                }
            }
        }
    });
}

let adminOrderGrowthChart = null;
async function loadOrderGrowth() {
    try {
        const response = await authFetch('/api/admin/order-growth');
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.success && data.data) {
            renderOrderGrowthChart(data.data);
        }
    } catch (err) {
        console.error('Order growth error:', err);
    }
}

function renderOrderGrowthChart(growthData) {
    const canvas = document.getElementById('orderGrowthChart');
    if (!canvas) return;
    
    if (adminOrderGrowthChart) {
        adminOrderGrowthChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    
    adminOrderGrowthChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Last Month', 'This Month'],
            datasets: [{
                label: 'Orders',
                data: [growthData.last_month, growthData.this_month],
                backgroundColor: ['#ff9800', '#4caf50'],
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            if (context.dataIndex === 1) {
                                return `Growth: ${growthData.growth_percentage}%`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 }
                }
            }
        }
    });
}

let adminUserGrowthChart = null;
async function loadUserGrowth() {
    try {
        const response = await authFetch('/api/admin/user-growth?days=30');
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.success && data.data) {
            renderUserGrowthChart(data.data);
        }
    } catch (err) {
        console.error('User growth error:', err);
    }
}

function renderUserGrowthChart(growthData) {
    const canvas = document.getElementById('userGrowthChart');
    if (!canvas) return;
    
    if (adminUserGrowthChart) {
        adminUserGrowthChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    const labels = growthData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const newUsers = growthData.map(d => d.new_users || 0);
    
    adminUserGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'New Users',
                data: newUsers,
                borderColor: '#2196f3',
                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y + ' new users';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

let adminApprovalChart = null;
async function loadApprovalBreakdown() {
    try {
        const response = await authFetch('/api/admin/approval-breakdown');
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.success && data.data) {
            renderApprovalBreakdownChart(data.data);
        }
    } catch (err) {
        console.error('Approval breakdown error:', err);
    }
}

function renderApprovalBreakdownChart(breakdownData) {
    const canvas = document.getElementById('approvalStatusChart');
    if (!canvas) return;
    
    if (adminApprovalChart) {
        adminApprovalChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    const total = breakdownData.total || {};
    
    adminApprovalChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Approved', 'Pending', 'Rejected'],
            datasets: [{
                data: [
                    total.approved || 0,
                    total.pending || 0,
                    total.rejected || 0
                ],
                backgroundColor: ['#4caf50', '#ff9800', '#f44336'],
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            return `${label}: ${value}`;
                        }
                    }
                }
            }
        }
    });
}

// Helper functions
function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} day${days > 1 ? 's' : ''} ago`;
    const months = Math.floor(days / 30);
    return `${months} month${months > 1 ? 's' : ''} ago`;
}

function getStatusClass(status) {
    const statusMap = {
        'placed': 'status-pending',
        'processing': 'status-pending',
        'dispatched': 'status-shipped',
        'delivered': 'status-completed',
        'cancelled': 'status-cancelled'
    };
    return statusMap[status] || 'status-pending';
}

window.loadSellersData = async function loadSellersData() {
    try {
        // Load seller statistics
        const statsResponse = await authFetch('/api/admin/sellers/stats');
        if (statsResponse.ok) {
            const statsData = await statsResponse.json();
            if (statsData.success) {
                const stats = statsData.stats;
                
                // Update stats cards
                if (document.getElementById('pendingCount')) {
                    document.getElementById('pendingCount').textContent = stats.pending || 0;
                }
                if (document.getElementById('approvedCount')) {
                    document.getElementById('approvedCount').textContent = stats.active || 0;
                }
                if (document.getElementById('declinedCount')) {
                    document.getElementById('declinedCount').textContent = stats.declined || 0;
                }
                if (document.getElementById('totalSellersCount')) {
                    document.getElementById('totalSellersCount').textContent = stats.total || 0;
                }
                
                // Update badge in sidebar
                const pendingBadge = document.getElementById('pendingSellersBadge');
                if (pendingBadge) {
                    const pendingCount = stats.pending || 0;
                    pendingBadge.textContent = pendingCount;
                    pendingBadge.style.display = pendingCount > 0 ? 'inline-block' : 'none';
                }
            }
        }
        
        // Load sellers list
        const response = await authFetch('/api/admin/sellers/pending?status=all&sort=created_at&order=desc');
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Failed to load sellers:', response.status, errorData);
            throw new Error(`Failed to load sellers: ${response.status} ${errorData.message || ''}`);
        }
        
        const data = await response.json();
        if (data.success) {
            sellers = data.sellers || [];
            renderSellersTable();
        } else {
            console.error('API returned success:false', data);
            throw new Error(data.message || 'Unknown error');
        }
    } catch (err) {
        console.error('Sellers data error:', err);
        // Show error in the table
        const tbody = document.getElementById('sellersTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: #f44336;">
                        <p style="font-size: 18px; margin-bottom: 10px;">⚠️</p>
                        <p>Error loading sellers</p>
                        <p style="font-size: 14px; color: #999; margin-top: 10px;">${err.message}</p>
                    </td>
                </tr>
            `;
        }
    }
}

window.loadRidersData = async function loadRidersData() {
    try {
        // Load rider statistics
        const statsResponse = await authFetch('/api/admin/riders/stats');
        if (statsResponse.ok) {
            const statsData = await statsResponse.json();
            if (statsData.success && statsData.stats) {
                updateRiderStats(statsData.stats);
            }
        }
        
        // Always load all riders after status changes to ensure we get the latest updates
        // The filter will be applied in renderRidersTable if needed
        await loadRidersWithFilter('all');
    } catch (err) {
        console.error('Riders data error:', err);
    }
}

// ==========================
// Discounts Approval (Admin)
// ==========================
async function loadPendingDiscounts() {
    try {
        console.log('Loading pending discounts...');
        const resp = await authFetch('/api/admin/pending-sales');
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
        }
        const data = await resp.json();
        console.log('Discounts response:', data);
        const items = data.data || data || [];
        const tbody = document.querySelector('#pendingDiscountsTable tbody');
        if (!tbody) {
            console.error('Table body not found for pendingDiscountsTable');
            return;
        }
        
        if (!items || items.length === 0) {
            // Hide the entire discount container when empty
            const discountContainer = document.getElementById('discountApprovalsContainer');
            if (discountContainer) {
                discountContainer.style.display = 'none';
            }
            tbody.innerHTML = '';
            
            // Update unified empty state
            if (typeof updateUnifiedEmptyState === 'function') {
                updateUnifiedEmptyState();
            }
            return;
        }
        
        // Show the discount container when we have data
        const discountContainer = document.getElementById('discountApprovalsContainer');
        if (discountContainer) {
            discountContainer.style.display = 'block';
        }
        
        tbody.innerHTML = items.map(d => {
            // Map backend fields to frontend display
            const discountPct = Number(d.discount_percentage || 0);
            const originalPrice = Number(d.original_price || 0);
            const salePrice = Number(d.sale_price || 0);
            const valueText = `${discountPct}% (₱${originalPrice.toFixed(2)} → ₱${salePrice.toFixed(2)})`;
            const sellerInfo = d.seller_name || d.seller_email || `User ${d.requested_by || 'N/A'}`;
            const startDate = d.valid_from ? new Date(d.valid_from).toLocaleDateString() : 'N/A';
            const endDate = d.valid_until ? new Date(d.valid_until).toLocaleDateString() : 'N/A';
            const productTitle = d.product_title || 'Unknown Product';
            const productImage = d.product_image || '';
            const daysUntilExpiry = d.days_until_expiry || 0;
            
            return `<tr style="border-bottom: 1px solid #f0f0f0; transition: background 0.2s;" onmouseover="this.style.background='#f8f9fa'" onmouseout="this.style.background='white'">
                <td style="padding: 16px 12px; color: #7f8c8d; font-weight: 600;">#${d.id}</td>
                <td style="padding: 16px 12px;" title="${d.seller_email || ''}">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 12px;">
                            ${sellerInfo.charAt(0).toUpperCase()}
                        </div>
                        <span style="color: #2c3e50; font-weight: 500;">${sellerInfo}</span>
                    </div>
                </td>
                <td style="padding: 16px 12px; color: #34495e; font-weight: 500;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${productImage ? `<img src="${productImage}" alt="${productTitle}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">` : ''}
                        <span>${productTitle}</span>
                    </div>
                </td>
                <td style="padding: 16px 12px; text-align: right; color: #27ae60; font-weight: 700; font-size: 14px;">${valueText}</td>
                <td style="padding: 16px 12px; text-align: center; color: #7f8c8d; font-size: 13px;">${startDate}</td>
                <td style="padding: 16px 12px; text-align: center; color: #7f8c8d; font-size: 13px;">${endDate}</td>
                <td style="padding: 16px 12px; text-align: center; color: ${daysUntilExpiry <= 7 ? '#e74c3c' : '#7f8c8d'}; font-size: 13px; font-weight: 600;">${daysUntilExpiry} days</td>
                <td style="padding: 16px 12px; text-align: center;">
                    <button onclick="approveDiscount(${d.id})" style="background: linear-gradient(135deg, #56ab2f, #a8e063); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-right: 6px; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                        <i class="fas fa-check"></i> APPROVE
                    </button>
                    <button onclick="declineDiscount(${d.id})" style="background: linear-gradient(135deg, #eb3349, #f45c43); color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                        <i class="fas fa-times"></i> DECLINE
                    </button>
                </td>
            </tr>`;
        }).join('');
        console.log(`Loaded ${items.length} pending discounts`);
        
        // Update unified empty state if available
        if (typeof updateUnifiedEmptyState === 'function') {
            updateUnifiedEmptyState();
        }
    } catch (e) {
        console.error('Failed to load pending discounts', e);
        const tbody = document.querySelector('#pendingDiscountsTable tbody');
        if (tbody) {
            tbody.innerHTML = `<tr>
                <td colspan="8" style="text-align:center; padding: 40px 20px;">
                    <div style="color: #e74c3c; font-size: 40px; margin-bottom: 12px;">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <p style="color: #e74c3c; font-size: 16px; margin: 0; font-weight: 600;">Error loading discounts</p>
                    <p style="color: #95a5a6; font-size: 14px; margin: 8px 0 0 0;">Please try refreshing the page</p>
                </td>
            </tr>`;
        }
    }
}

async function approveDiscount(id) {
    try {
        const resp = await authFetch(`/api/admin/sales/${id}/approve`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
        const data = await resp.json();
        if (resp.ok && data.success) {
            notify.success('Discount approved');
            loadPendingDiscounts();
        } else {
            notify.error(data.error || data.message || 'Failed to approve');
        }
    } catch (e) {
        console.error('Approve discount error', e);
        notify.error('Error approving discount: ' + e.message);
    }
}

async function declineDiscount(id) {
    try {
        const note = prompt('Optional note for decline:');
        const resp = await authFetch(`/api/admin/sales/${id}/reject`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ notes: note || 'Rejected by admin' }) });
        const data = await resp.json();
        if (resp.ok && data.success) {
            notify.success('Discount declined');
            loadPendingDiscounts();
        } else {
            notify.error(data.error || data.message || 'Failed to decline');
        }
    } catch (e) {
        console.error('Decline discount error', e);
        notify.error('Error declining discount');
    }
}

// Update rider statistics display
function updateRiderStats(stats) {
    // Update stat cards
    document.getElementById('riderPendingCount').textContent = stats.pending || 0;
    document.getElementById('riderApprovedCount').textContent = stats.active || 0;
    document.getElementById('riderDeclinedCount').textContent = stats.declined || 0;
    document.getElementById('totalRidersCount').textContent = stats.total || 0;
}

// Load riders with status filter
async function loadRidersWithFilter(status) {
    try {
        const searchTerm = document.getElementById('riderSearch')?.value || '';
        let url = `/api/admin/riders/pending?status=${status}`;
        if (searchTerm) {
            url += `&search=${encodeURIComponent(searchTerm)}`;
        }
        
        // Add timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
        
        const response = await authFetch(url, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        if (!response.ok) throw new Error('Failed to load riders');
        
        const data = await response.json();
        if (data.success) {
            riders = data.data || [];
            renderRidersTable();
        }
    } catch (err) {
        console.error('Load riders error:', err);
        if (err.name === 'AbortError') {
            console.error('Request timed out after 10 seconds');
            showNotification('Request timed out. Please refresh the page.', 'warning');
        }
        // Don't clear riders array on error - keep existing data
        renderRidersTable();
    }
}

window.loadOrdersData = async function loadOrdersData() {
    try {
        const response = await authFetch('/api/admin/orders');
        if (!response.ok) throw new Error('Failed to load orders');
        
        const data = await response.json();
        if (data.success) {
            orders = data.orders || [];
            renderOrdersTable();
        }
    } catch (err) {
        console.error('Orders data error:', err);
    }
}

// ============== Rendering ==============
function renderSellersTable() {
    const tbody = document.getElementById('sellersTableBody');
    if (!tbody) return;
    
    if (sellers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px; color: #999;">
                    <p style="font-size: 18px; margin-bottom: 10px;">📋</p>
                    <p>No sellers found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    // Group sellers by ID to avoid duplicates
    const uniqueSellers = {};
    sellers.forEach(seller => {
        if (!uniqueSellers[seller.id]) {
            uniqueSellers[seller.id] = seller;
        }
    });
    const sellerList = Object.values(uniqueSellers);
    
    tbody.innerHTML = sellerList.map(seller => {
        // Use account_status if available, otherwise fall back to shop_status, then default to 'pending'
        const sellerStatus = seller.account_status || seller.shop_status || seller.status || 'pending';
        const statusBadge = getStatusBadge(sellerStatus);
        const ownerName = [seller.first_name, seller.last_name].filter(Boolean).join(' ') || 'N/A';
        const joinedDate = new Date(seller.created_at).toLocaleDateString('en-US', { 
            year: 'numeric', month: 'short', day: 'numeric' 
        });
        return `
            <tr class="seller-row" data-seller-id="${seller.id}">
                <td style="text-align: center;"></td>
                <td>${seller.id}</td>
                <td><strong>${seller.business_name || 'N/A'}</strong></td>
                <td>${ownerName}</td>
                <td>${seller.email}</td>
                <td>${statusBadge}</td>
                <td>${joinedDate}</td>
                <td style="white-space: nowrap;">
                    <button class="btn btn-sm btn-primary" onclick="viewSellerDetails(${seller.id})" 
                            title="View Details" style="padding: 6px 10px; font-size: 13px; min-width: auto; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; margin-right: 5px;">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSeller(${seller.id}, '${(seller.business_name || '').replace(/'/g, "\\'")}')" 
                            title="Delete Seller" style="padding: 6px 10px; font-size: 13px; min-width: auto; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// Get status badge HTML
function getStatusBadge(status) {
    if (!status || status === 'null' || status === 'undefined') {
        return '<span class="status-badge status-pending">⏳ Pending</span>';
    }
    const statusLower = String(status).toLowerCase();
    const badges = {
        'pending': '<span class="status-badge status-pending">⏳ Pending</span>',
        'active': '<span class="status-badge status-approved">✅ Approved</span>',
        'declined': '<span class="status-badge status-rejected">❌ Declined</span>',
        'suspended': '<span class="status-badge status-rejected">⏸️ Suspended</span>',
        'warning': '<span class="status-badge status-warning">⚠️ Warning</span>',
        'banned': '<span class="status-badge status-banned">🔨 Banned</span>'
    };
    return badges[statusLower] || `<span class="status-badge status-pending">⏳ ${String(status).charAt(0).toUpperCase() + String(status).slice(1)}</span>`;
}

// Truncate text helper
function truncate(text, maxLength) {
    if (!text) return 'N/A';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// Store management removed - single store per seller

// Filter sellers by status
window.filterSellersByStatus = function(button) {
    // Update active button
    document.querySelectorAll('#sellersSection .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    button.classList.add('active');
    
    // Get status from button
    const status = button.getAttribute('data-status');
    
    // Reload sellers with filter
    loadSellersWithFilter(status);
};

// Load sellers with filter
async function loadSellersWithFilter(status) {
    try {
        const response = await authFetch(`/api/admin/sellers/pending?status=${status}&sort=created_at&order=desc`);
        if (!response.ok) throw new Error('Failed to load sellers');
        
        const data = await response.json();
        if (data.success) {
            sellers = data.sellers || [];
            renderSellersTable();
        }
    } catch (err) {
        console.error('Filter sellers error:', err);
    }
}

// Filter sellers by search
window.filterSellers = function() {
    const searchTerm = document.getElementById('sellerSearch').value.toLowerCase();
    
    const filtered = sellers.filter(seller => {
        return (
            (seller.business_name && seller.business_name.toLowerCase().includes(searchTerm)) ||
            (seller.email && seller.email.toLowerCase().includes(searchTerm)) ||
            (seller.first_name && seller.first_name.toLowerCase().includes(searchTerm)) ||
            (seller.last_name && seller.last_name.toLowerCase().includes(searchTerm))
        );
    });
    
    // Temporarily replace sellers array for rendering
    const originalSellers = sellers;
    sellers = filtered;
    renderSellersTable();
    sellers = originalSellers;
};

// View seller details
window.viewSellerDetails = async function(sellerId) {
    try {
        const response = await authFetch(`/api/admin/sellers/${sellerId}`);
        if (!response.ok) throw new Error('Failed to load seller details');
        
        const data = await response.json();
        if (data.success) {
            selectedSellerForReview = data.seller;
            const auditLog = data.audit_log || [];
            displaySellerReviewModal(data.seller, auditLog);
            
            // Open modal
            const modal = document.getElementById('sellerReviewModal');
            if (modal) modal.style.display = 'block';
        }
    } catch (err) {
        console.error('View seller details error:', err);
        alert('Failed to load seller details: ' + err.message);
    }
};

function renderRidersTable() {
    const container = document.getElementById('ridersTableContainer');
    if (!container) return;
    
    if (riders.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 20px;">No riders found</p>';
        return;
    }
    
    const html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Vehicle Type</th>
                    <th>License</th>
                    <th>Status</th>
                    <th>Joined</th>
                </tr>
            </thead>
            <tbody>
                ${riders.map(r => `
                    <tr>
                        <td><strong>${r.first_name || ''} ${r.last_name || ''}</strong></td>
                        <td>${r.email || ''}</td>
                        <td>${r.vehicle_type || 'N/A'}</td>
                        <td>${r.driver_license ? 'Verified' : 'Pending'}</td>
                        <td><span class="status-badge ${r.verified ? 'verified' : 'pending'}">${r.verified ? 'Verified' : 'Pending'}</span></td>
                        <td>${new Date(r.created_at).toLocaleDateString()}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function renderOrdersTable() {
    const container = document.getElementById('ordersTableContainer');
    if (!container) return;
    
    if (orders.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 20px;">No orders found</p>';
        return;
    }
    
    const html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Customer</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Payment</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                ${orders.map(o => `
                    <tr>
                        <td><strong>#${o.id}</strong></td>
                        <td>${o.customer_name || 'N/A'}</td>
                        <td>₱${(o.total || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
                        <td><span class="status-badge ${getStatusClass(o.status)}">${o.status || 'pending'}</span></td>
                        <td>${o.payment || 'N/A'}</td>
                        <td>${new Date(o.created_at).toLocaleDateString()}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function getStatusClass(status) {
    const statusMap = {
        'placed': 'pending',
        'confirmed': 'pending',
        'dispatched': 'in-progress',
        'in-transit': 'in-progress',
        'delivered': 'success',
        'cancelled': 'cancelled'
    };
    return statusMap[status] || 'pending';
}

function initializeDashboardCharts() {
    // User Growth Chart
    destroyChart('userGrowthChart');
    const userGrowthCtx = document.getElementById('userGrowthChart');
    if (userGrowthCtx) {
        chartInstances['userGrowthChart'] = new Chart(userGrowthCtx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Sellers',
                    data: [8, 10, 12, 13],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Riders',
                    data: [12, 15, 18, 21],
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'top' } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    // Registration Distribution Pie Chart
    destroyChart('registrationChart');
    const registrationCtx = document.getElementById('registrationChart');
    if (registrationCtx) {
        const approvedSellers = sellers.filter(s => s.status === 'approved').length;
        const pendingSellers = sellers.filter(s => s.status === 'pending').length;
        const rejectedSellers = sellers.filter(s => s.status === 'rejected').length;
        
        chartInstances['registrationChart'] = new Chart(registrationCtx, {
            type: 'pie',
            data: {
                labels: ['Approved', 'Pending', 'Rejected'],
                datasets: [{
                    data: [approvedSellers, pendingSellers, rejectedSellers],
                    backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c'],
                    borderColor: '#fff',
                    borderWidth: 2
                }]
            },
            options: { responsive: true, maintainAspectRatio: true }
        });
    }

    // Approval Status Breakdown
    destroyChart('approvalStatusChart');
    const approvalCtx = document.getElementById('approvalStatusChart');
    if (approvalCtx) {
        const allApproved = sellers.filter(s => s.status === 'approved').length + riders.filter(r => r.status === 'approved').length;
        const allPending = sellers.filter(s => s.status === 'pending').length + riders.filter(r => r.status === 'pending').length;
        const allRejected = sellers.filter(s => s.status === 'rejected').length + riders.filter(r => r.status === 'rejected').length;
        
        chartInstances['approvalStatusChart'] = new Chart(approvalCtx, {
            type: 'doughnut',
            data: {
                labels: ['Approved', 'Pending', 'Rejected'],
                datasets: [{
                    data: [allApproved, allPending, allRejected],
                    backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c'],
                    borderColor: '#fff',
                    borderWidth: 2
                }]
            },
            options: { responsive: true, maintainAspectRatio: true }
        });
    }

    // Revenue by Category
    destroyChart('revenueCategoryChart');
    const revenueCategoryCtx = document.getElementById('revenueCategoryChart');
    if (revenueCategoryCtx) {
        const categories = {};
        sellers.forEach(s => {
            categories[s.category] = (categories[s.category] || 0) + s.revenue;
        });
        
        chartInstances['revenueCategoryChart'] = new Chart(revenueCategoryCtx, {
            type: 'bar',
            data: {
                labels: Object.keys(categories),
                datasets: [{
                    label: 'Revenue (₱)',
                    data: Object.values(categories),
                    backgroundColor: '#3498db'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    // Vehicle Type Distribution
    destroyChart('vehicleTypeChart');
    const vehicleTypeCtx = document.getElementById('vehicleTypeChart');
    if (vehicleTypeCtx) {
        const vehicleTypes = {};
        riders.forEach(r => {
            vehicleTypes[r.vehicleType] = (vehicleTypes[r.vehicleType] || 0) + 1;
        });
        
        chartInstances['vehicleTypeChart'] = new Chart(vehicleTypeCtx, {
            type: 'radar',
            data: {
                labels: Object.keys(vehicleTypes).map(v => capitalizeText(v)),
                datasets: [{
                    label: 'Number of Riders',
                    data: Object.values(vehicleTypes),
                    borderColor: '#9b59b6',
                    backgroundColor: 'rgba(155, 89, 182, 0.2)'
                }]
            },
            options: { responsive: true, maintainAspectRatio: true }
        });
    }

    // Seller Category Distribution
    destroyChart('sellerCategoryChart');
    const sellerCategoryCtx = document.getElementById('sellerCategoryChart');
    if (sellerCategoryCtx) {
        const sellerCategories = {};
        sellers.forEach(s => {
            sellerCategories[s.category] = (sellerCategories[s.category] || 0) + 1;
        });
        
        chartInstances['sellerCategoryChart'] = new Chart(sellerCategoryCtx, {
            type: 'polarArea',
            data: {
                labels: Object.keys(sellerCategories).map(c => capitalizeText(c)),
                datasets: [{
                    data: Object.values(sellerCategories),
                    backgroundColor: ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
                }]
            },
            options: { responsive: true, maintainAspectRatio: true }
        });
    }
}

// ============== Reports Module ==============
let reportsData = null;

async function loadReportsData() {
    console.log('📊 loadReportsData called');
    const dateRange = document.getElementById('dateRangeFilter')?.value || 'month';
    const startDate = document.getElementById('startDate')?.value || '';
    const endDate = document.getElementById('endDate')?.value || '';
    
    console.log('📊 Loading reports with dateRange:', dateRange);
    
    // Show loading states
    showReportsLoading(true);
    
    try {
        let url = `/api/admin/reports/data?period=${dateRange}`;
        if (dateRange === 'custom' && startDate && endDate) {
            url += `&start_date=${startDate}&end_date=${endDate}`;
        }
        
        console.log('📊 Fetching from URL:', url);
        const response = await authFetch(url);
        if (!response.ok) {
            throw new Error(`Failed to load reports data: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('📊 Reports data received:', result);
        
        if (result.success && result.data) {
            reportsData = result.data;
            console.log('📊 Reports data set, updating charts...');
            updateAllReportCharts();
            console.log('📊 Charts updated successfully');
        } else {
            console.error('❌ Invalid reports data:', result);
            showReportsError('Failed to load reports data');
        }
    } catch (error) {
        console.error('❌ Error loading reports data:', error);
        showReportsError('Error loading reports: ' + error.message);
    } finally {
        showReportsLoading(false);
        // Update summary AFTER clearing loading state to prevent overwriting
        if (reportsData && reportsData.summary) {
            updateReportsSummary();
        }
        console.log('📊 Loading state cleared');
    }
}

// Expose globally
window.loadReportsData = loadReportsData;

function showReportsLoading(show) {
    const charts = ['registrationTrendChart', 'performanceChart', 'revenueAnalyticsChart', 'satisfactionChart'];
    charts.forEach(chartId => {
        const container = document.getElementById(chartId)?.parentElement;
        if (!container) return;
        
        if (show) {
            // Store the canvas if it exists
            const existingCanvas = container.querySelector('canvas');
            if (existingCanvas) {
                existingCanvas.setAttribute('data-chart-id', chartId);
                existingCanvas.style.display = 'none';
            }
            
            // Add loading overlay
            let loadingDiv = container.querySelector('.chart-loading');
            if (!loadingDiv) {
                loadingDiv = document.createElement('div');
                loadingDiv.className = 'chart-loading';
                loadingDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #999; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.9); z-index: 10;';
                loadingDiv.innerHTML = `
                    <i class="fas fa-spinner fa-spin" style="font-size: 32px; margin-bottom: 10px;"></i>
                    <p>Loading chart data...</p>
                `;
                container.style.position = 'relative';
                container.appendChild(loadingDiv);
            } else {
                loadingDiv.style.display = 'flex';
            }
        } else {
            // Hide loading overlay
            const loadingDiv = container.querySelector('.chart-loading');
            if (loadingDiv) {
                loadingDiv.style.display = 'none';
            }
            
            // Restore canvas if it was hidden
            const hiddenCanvas = container.querySelector('canvas[data-chart-id="' + chartId + '"]');
            if (hiddenCanvas) {
                hiddenCanvas.style.display = 'block';
                hiddenCanvas.removeAttribute('data-chart-id');
            } else if (!container.querySelector('canvas')) {
                // Create new canvas if none exists
                const canvas = document.createElement('canvas');
                canvas.id = chartId;
                container.appendChild(canvas);
            }
        }
    });
    
    // Show loading for summary cards
    const summaryCards = ['summaryTotalUsers', 'summaryApprovedUsers', 'summaryApprovalRate', 'summaryResponseTime'];
    summaryCards.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (show) {
                // Only save original if we haven't already set real data
                if (!el.hasAttribute('data-original-text')) {
                    el.setAttribute('data-original-text', el.textContent);
                }
                el.textContent = '...';
            } else {
                // Don't restore original if we have real data to show
                // The updateReportsSummary() will set the correct values
                // Just remove the loading indicator
                const original = el.getAttribute('data-original-text');
                if (original && original !== '...') {
                    // Only restore if it's not the loading indicator
                    // But actually, we want updateReportsSummary to set the real values
                    // So we'll just remove the attribute and let updateReportsSummary handle it
                }
                // Don't restore here - let updateReportsSummary set the real values
            }
        }
    });
}

function showReportsError(message) {
    const charts = ['registrationTrendChart', 'performanceChart', 'revenueAnalyticsChart', 'satisfactionChart'];
    charts.forEach(chartId => {
        const container = document.getElementById(chartId)?.parentElement;
        if (!container) return;
        
        // Remove loading overlay
        const loadingDiv = container.querySelector('.chart-loading');
        if (loadingDiv) loadingDiv.remove();
        
        // Hide canvas if it exists
        const canvas = container.querySelector('canvas');
        if (canvas) canvas.style.display = 'none';
        
        // Show error message
        let errorDiv = container.querySelector('.chart-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'chart-error';
            errorDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #e74c3c;';
            container.appendChild(errorDiv);
        }
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 10px;"></i>
            <p>${message}</p>
        `;
        errorDiv.style.display = 'flex';
    });
}

function handleDateRangeChange() {
    const dateRange = document.getElementById('dateRangeFilter').value;
    const customRangeDiv = document.getElementById('customDateRange');
    
    if (dateRange === 'custom') {
        customRangeDiv.style.display = 'flex';
        // Set default dates (last 30 days)
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 30);
        document.getElementById('endDate').value = end.toISOString().split('T')[0];
        document.getElementById('startDate').value = start.toISOString().split('T')[0];
    } else {
        customRangeDiv.style.display = 'none';
        loadReportsData();
    }
}

function applyCustomDateRange() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        alert('Please select both start and end dates');
        return;
    }
    
    if (new Date(startDate) > new Date(endDate)) {
        alert('Start date must be before end date');
        return;
    }
    
    loadReportsData();
}

function updateAllReportCharts() {
    console.log('📊 updateAllReportCharts called, reportsData:', reportsData);
    if (!reportsData) {
        console.warn('⚠️ No reports data available');
        return;
    }
    
    console.log('📊 Updating all charts...');
    updateRegistrationChart();
    updatePerformanceChart();
    updateRevenueChart();
    updateSatisfactionChart();
    console.log('📊 All charts updated');
}

function updateRegistrationChart() {
    console.log('📊 updateRegistrationChart called');
    destroyChart('registrationTrendChart');
    
    // Find container by looking for the report card with the title
    let container = null;
    const reportCards = document.querySelectorAll('.report-card-large');
    for (let card of reportCards) {
        const h3 = card.querySelector('h3');
        if (h3) {
            const titleText = h3.textContent.trim();
            // Check if title matches (exact or contains)
            if (titleText === 'User Registrations Trend' || titleText.includes('User Registrations')) {
                container = card;
                console.log('📊 Found container by title:', container, 'Title:', titleText);
                break;
            }
        }
    }
    
    // Fallback: try to find by canvas ID
    if (!container) {
        const canvas = document.getElementById('registrationTrendChart');
        if (canvas && canvas.parentElement) {
            container = canvas.parentElement;
            console.log('📊 Found container via canvas parent:', container);
        }
    }
    
    // Last resort: find by position (first report card)
    if (!container && reportCards.length > 0) {
        container = reportCards[0];
        console.log('📊 Using first report card as fallback:', container);
    }
    
    if (!container) {
        console.error('❌ Container not found for registrationTrendChart. Available report cards:', reportCards.length);
        // Log all available titles for debugging
        reportCards.forEach((card, idx) => {
            const h3 = card.querySelector('h3');
            console.log(`  Card ${idx}:`, h3 ? h3.textContent.trim() : 'No h3 found');
        });
        return;
    }
    
    updateRegistrationChartInContainer(container);
}

function updateRegistrationChartInContainer(container) {
    // Remove empty state if it exists
    const existingEmpty = container.querySelector('.chart-empty-state');
    if (existingEmpty) existingEmpty.remove();
    
    // Remove loading and error overlays
    const loadingDiv = container.querySelector('.chart-loading');
    if (loadingDiv) loadingDiv.remove();
    const errorDiv = container.querySelector('.chart-error');
    if (errorDiv) errorDiv.remove();
    
    // Ensure canvas exists
    let trendCtx = document.getElementById('registrationTrendChart');
    if (!trendCtx) {
        trendCtx = document.createElement('canvas');
        trendCtx.id = 'registrationTrendChart';
        container.appendChild(trendCtx);
        console.log('📊 Created new canvas for registrationTrendChart');
    }
    
    // Show canvas
    if (trendCtx) trendCtx.style.display = 'block';
    
    if (!reportsData || !reportsData.registrations || reportsData.registrations.length === 0) {
        console.warn('⚠️ No registration data available');
        // Show empty state - preserve h3 title
        const h3 = container.querySelector('h3');
        const existingEmpty = container.querySelector('.chart-empty-state');
        if (existingEmpty) existingEmpty.remove();
        
        // Remove canvas if it exists
        if (trendCtx) trendCtx.remove();
        
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'chart-empty-state';
        emptyDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #999;';
        emptyDiv.innerHTML = `
            <i class="fas fa-chart-line" style="font-size: 48px; margin-bottom: 10px; opacity: 0.3;"></i>
            <p>No registration data available for the selected period</p>
        `;
        container.appendChild(emptyDiv);
        return;
    }
    
    console.log('📊 Registration data:', reportsData.registrations);
    
    // Group by date and role
    const dateMap = {};
    reportsData.registrations.forEach(item => {
        const date = item.date;
        if (!dateMap[date]) {
            dateMap[date] = { date, total: 0, customer: 0, seller: 0, rider: 0, admin: 0 };
        }
        dateMap[date].total += item.count;
        if (item.role) {
            dateMap[date][item.role] = (dateMap[date][item.role] || 0) + item.count;
        }
    });
    
    const sortedDates = Object.keys(dateMap).sort();
    const labels = sortedDates.map(d => {
        const date = new Date(d);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    chartInstances['registrationTrendChart'] = new Chart(trendCtx, {
            type: 'line',
            data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Registrations',
                    data: sortedDates.map(d => dateMap[d].total),
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Customers',
                    data: sortedDates.map(d => dateMap[d].customer || 0),
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3
                },
                {
                    label: 'Sellers',
                    data: sortedDates.map(d => dateMap[d].seller || 0),
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3
                },
                {
                    label: 'Riders',
                    data: sortedDates.map(d => dateMap[d].rider || 0),
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3
                }
            ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
            plugins: { 
                legend: { position: 'top' },
                title: { display: true, text: 'User Registrations Trend' }
            },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

function updatePerformanceChart() {
    destroyChart('performanceChart');
    
    // Find container by title
    let container = null;
    const reportCards = document.querySelectorAll('.report-card-large');
    for (let card of reportCards) {
        const h3 = card.querySelector('h3');
        if (h3 && h3.textContent.trim() === 'Platform Performance Metrics') {
            container = card;
            break;
        }
    }
    
    // Fallback: try to find by canvas ID
    if (!container) {
        const canvas = document.getElementById('performanceChart');
        if (canvas && canvas.parentElement) {
            container = canvas.parentElement;
        }
    }
    
    if (!container) {
        console.error('❌ Container not found for performanceChart');
        return;
    }
    
    updatePerformanceChartInContainer(container);
}

function updatePerformanceChartInContainer(container) {
    // Ensure canvas exists
    let perfCtx = document.getElementById('performanceChart');
    if (!perfCtx) {
        perfCtx = document.createElement('canvas');
        perfCtx.id = 'performanceChart';
        container.appendChild(perfCtx);
    }
    
    if (!perfCtx) {
        perfCtx = document.createElement('canvas');
        perfCtx.id = 'performanceChart';
        container.appendChild(perfCtx);
    }
    
    // Remove loading and error overlays
    const loadingDiv = container.querySelector('.chart-loading');
    if (loadingDiv) loadingDiv.remove();
    const errorDiv = container.querySelector('.chart-error');
    if (errorDiv) errorDiv.remove();
    
    // Show canvas
    if (perfCtx) perfCtx.style.display = 'block';
    
    if (!reportsData || !reportsData.performance) {
        // Show empty state - preserve h3 title
        const existingEmpty = container.querySelector('.chart-empty-state');
        if (existingEmpty) existingEmpty.remove();
        
        // Remove canvas if it exists
        if (perfCtx) perfCtx.remove();
        
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'chart-empty-state';
        emptyDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #999;';
        emptyDiv.innerHTML = `
            <i class="fas fa-chart-bar" style="font-size: 48px; margin-bottom: 10px; opacity: 0.3;"></i>
            <p>No performance data available</p>
        `;
        container.appendChild(emptyDiv);
        return;
    }
    
    const perf = reportsData.performance;
    
    chartInstances['performanceChart'] = new Chart(perfCtx, {
            type: 'bar',
            data: {
            labels: ['System Uptime', 'Avg Server Load', 'API Requests', 'Total Orders'],
                datasets: [{
                label: 'Performance Metrics',
                data: [
                    perf.uptime_percentage,
                    perf.avg_server_load,
                    Math.min(100, (perf.api_request_volume / 1000) * 10), // Normalize to 0-100
                    Math.min(100, (perf.total_orders / 100) * 10) // Normalize to 0-100
                ],
                backgroundColor: ['#2ecc71', '#27ae60', '#16a085', '#3498db']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                title: { display: true, text: 'Platform Performance Metrics' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const labels = ['Uptime (%)', 'Server Load (%)', 'API Requests (normalized)', 'Orders (normalized)'];
                            const values = [
                                perf.uptime_percentage.toFixed(1) + '%',
                                perf.avg_server_load.toFixed(1) + '%',
                                perf.api_request_volume.toLocaleString(),
                                perf.total_orders.toLocaleString()
                            ];
                            return labels[context.dataIndex] + ': ' + values[context.dataIndex];
                        }
                    }
                }
            },
                scales: { y: { beginAtZero: true, max: 100 } }
            }
        });
    }

function updateRevenueChart() {
    destroyChart('revenueAnalyticsChart');
    
    // Find container by title
    let container = null;
    const reportCards = document.querySelectorAll('.report-card-large');
    for (let card of reportCards) {
        const h3 = card.querySelector('h3');
        if (h3 && h3.textContent.trim() === 'Revenue Analytics') {
            container = card;
            break;
        }
    }
    
    // Fallback: try to find by canvas ID
    if (!container) {
        const canvas = document.getElementById('revenueAnalyticsChart');
        if (canvas && canvas.parentElement) {
            container = canvas.parentElement;
        }
    }
    
    if (!container) {
        console.error('❌ Container not found for revenueAnalyticsChart');
        return;
    }
    
    updateRevenueChartInContainer(container);
}

function updateRevenueChartInContainer(container) {
    // Remove empty state if it exists
    const existingEmpty = container.querySelector('.chart-empty-state');
    if (existingEmpty) existingEmpty.remove();
    
    // Remove loading and error overlays
    const loadingDiv = container.querySelector('.chart-loading');
    if (loadingDiv) loadingDiv.remove();
    const errorDiv = container.querySelector('.chart-error');
    if (errorDiv) errorDiv.remove();
    
    // Ensure canvas exists
    let revenueCtx = document.getElementById('revenueAnalyticsChart');
    if (!revenueCtx) {
        revenueCtx = document.createElement('canvas');
        revenueCtx.id = 'revenueAnalyticsChart';
        container.appendChild(revenueCtx);
    }
    
    // Show canvas
    if (revenueCtx) revenueCtx.style.display = 'block';
    
    if (!reportsData || !reportsData.revenue || reportsData.revenue.length === 0) {
        // Show empty state - preserve h3 title
        const existingEmpty = container.querySelector('.chart-empty-state');
        if (existingEmpty) existingEmpty.remove();
        
        // Remove canvas if it exists
        if (revenueCtx) revenueCtx.remove();
        
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'chart-empty-state';
        emptyDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #999;';
        emptyDiv.innerHTML = `
            <i class="fas fa-chart-line" style="font-size: 48px; margin-bottom: 10px; opacity: 0.3;"></i>
            <p>No revenue data available for the selected period</p>
        `;
        container.appendChild(emptyDiv);
        return;
    }
    
    const revenueData = reportsData.revenue;
    const labels = revenueData.map(r => {
        const date = new Date(r.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    chartInstances['revenueAnalyticsChart'] = new Chart(revenueCtx, {
            type: 'line',
            data: {
            labels: labels,
            datasets: [
                {
                    label: 'Daily Revenue (₱)',
                    data: revenueData.map(r => r.revenue),
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Orders Count',
                    data: revenueData.map(r => r.orders),
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top' },
                title: { display: true, text: 'Revenue Analytics' }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₱' + value.toLocaleString();
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: true,
                    grid: { drawOnChartArea: false }
                }
            }
            }
        });
    }

function updateSatisfactionChart() {
    destroyChart('satisfactionChart');
    
    // Find container by title
    let container = null;
    const reportCards = document.querySelectorAll('.report-card-large');
    for (let card of reportCards) {
        const h3 = card.querySelector('h3');
        if (h3 && h3.textContent.trim() === 'User Satisfaction Rate') {
            container = card;
            break;
        }
    }
    
    // Fallback: try to find by canvas ID
    if (!container) {
        const canvas = document.getElementById('satisfactionChart');
        if (canvas && canvas.parentElement) {
            container = canvas.parentElement;
        }
    }
    
    if (!container) {
        console.error('❌ Container not found for satisfactionChart');
        return;
    }
    
    updateSatisfactionChartInContainer(container);
}

function updateSatisfactionChartInContainer(container) {
    // Remove empty state if it exists
    const existingEmpty = container.querySelector('.chart-empty-state');
    if (existingEmpty) existingEmpty.remove();
    
    // Remove loading and error overlays
    const loadingDiv = container.querySelector('.chart-loading');
    if (loadingDiv) loadingDiv.remove();
    const errorDiv = container.querySelector('.chart-error');
    if (errorDiv) errorDiv.remove();
    
    // Ensure canvas exists
    let satisfactionCtx = document.getElementById('satisfactionChart');
    if (!satisfactionCtx) {
        satisfactionCtx = document.createElement('canvas');
        satisfactionCtx.id = 'satisfactionChart';
        container.appendChild(satisfactionCtx);
    }
    
    // Show canvas
    if (satisfactionCtx) satisfactionCtx.style.display = 'block';
    
    if (!reportsData || !reportsData.satisfaction || !reportsData.satisfaction.total_ratings || reportsData.satisfaction.total_ratings === 0) {
        // Show empty state - preserve h3 title
        const existingEmpty = container.querySelector('.chart-empty-state');
        if (existingEmpty) existingEmpty.remove();
        
        // Remove canvas if it exists
        if (satisfactionCtx) satisfactionCtx.remove();
        
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'chart-empty-state';
        emptyDiv.style.cssText = 'display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; color: #999;';
        emptyDiv.innerHTML = `
            <i class="fas fa-star" style="font-size: 48px; margin-bottom: 10px; opacity: 0.3;"></i>
            <p>No satisfaction data available for the selected period</p>
        `;
        container.appendChild(emptyDiv);
        return;
    }
    
    const sat = reportsData.satisfaction;
    const distribution = sat.distribution || {1: 0, 2: 0, 3: 0, 4: 0, 5: 0};
    
    chartInstances['satisfactionChart'] = new Chart(satisfactionCtx, {
        type: 'bar',
            data: {
            labels: ['1 Star', '2 Stars', '3 Stars', '4 Stars', '5 Stars'],
                datasets: [{
                label: 'Rating Distribution',
                data: [distribution[1], distribution[2], distribution[3], distribution[4], distribution[5]],
                backgroundColor: ['#e74c3c', '#e67e22', '#f39c12', '#3498db', '#2ecc71']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                title: { 
                    display: true, 
                    text: `User Satisfaction Rate - Average: ${sat.average || 0}/5 (${((sat.average || 0) / 5 * 100).toFixed(1)}%) - ${sat.total_ratings || 0} ratings` 
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = sat.total_ratings || 1;
                            const value = context.parsed.y;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${value} ratings (${percentage}%)`;
                        }
                    }
                }
            },
            scales: { y: { beginAtZero: true } }
        }
    });
}

function updateReportsSummary() {
    console.log('📊 updateReportsSummary called, reportsData:', reportsData);
    
    if (!reportsData) {
        console.warn('⚠️ No reportsData available');
        return;
    }
    
    if (!reportsData.summary) {
        console.warn('⚠️ No summary data in reportsData:', reportsData);
        return;
    }
    
    const summary = reportsData.summary;
    console.log('📊 Summary data:', summary);
    
    const totalUsersEl = document.getElementById('summaryTotalUsers');
    const approvedUsersEl = document.getElementById('summaryApprovedUsers');
    const approvalRateEl = document.getElementById('summaryApprovalRate');
    const responseTimeEl = document.getElementById('summaryResponseTime');
    
    console.log('📊 Summary elements found:', {
        totalUsers: !!totalUsersEl,
        approvedUsers: !!approvedUsersEl,
        approvalRate: !!approvalRateEl,
        responseTime: !!responseTimeEl
    });
    
    if (totalUsersEl) {
        totalUsersEl.textContent = summary.total_users || 0;
        console.log('📊 Set totalUsers:', summary.total_users || 0);
    }
    if (approvedUsersEl) {
        approvedUsersEl.textContent = summary.approved_users || 0;
        console.log('📊 Set approvedUsers:', summary.approved_users || 0);
    }
    if (approvalRateEl) {
        approvalRateEl.textContent = (summary.approval_rate || 0).toFixed(1) + '%';
        console.log('📊 Set approvalRate:', summary.approval_rate || 0);
    }
    if (responseTimeEl) {
        const hours = summary.avg_response_time_hours || 0;
        let formattedTime = '0h';
        if (hours < 1) {
            formattedTime = (hours * 60).toFixed(0) + 'm';
        } else if (hours < 24) {
            formattedTime = hours.toFixed(1) + 'h';
        } else {
            formattedTime = (hours / 24).toFixed(1) + 'd';
        }
        responseTimeEl.textContent = formattedTime;
        console.log('📊 Set responseTime:', hours, '->', formattedTime);
    }
}

function initializeReportCharts() {
    loadReportsData();
}

function updateReports() {
    loadReportsData();
}

// PDF Export functionality
function printReport() {
    if (!reportsData) {
        alert('Please wait for reports to load');
        return;
    }
    
    // Create a new window for printing
    const printWindow = window.open('', '_blank');
    const dateRange = document.getElementById('dateRangeFilter').value;
    const dateRangeText = document.getElementById('dateRangeFilter').options[document.getElementById('dateRangeFilter').selectedIndex].text;
    
    // Get platform name
    const platformName = document.getElementById('platformName')?.value || localStorage.getItem('platform_name') || 'Hub';
    
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${platformName} - Admin Reports - ${dateRangeText}</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 30px; }
                .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
                .summary-card { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
                .summary-label { font-size: 12px; color: #666; margin-bottom: 5px; }
                .summary-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background: #3498db; color: white; }
                .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center; }
            </style>
        </head>
        <body>
            <h1>${platformName} - Admin Dashboard Reports</h1>
            <p><strong>Date Range:</strong> ${dateRangeText}</p>
            <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
            
            <h2>Summary Metrics</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-label">Total Users</div>
                    <div class="summary-value">${reportsData.summary.total_users || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="summary-label">Approved Users</div>
                    <div class="summary-value">${reportsData.summary.approved_users || 0}</div>
                </div>
                <div class="summary-card">
                    <div class="summary-label">Approval Rate</div>
                    <div class="summary-value">${(reportsData.summary.approval_rate || 0).toFixed(1)}%</div>
                </div>
                <div class="summary-card">
                    <div class="summary-label">Avg Response Time</div>
                    <div class="summary-value">${(reportsData.summary.avg_response_time_hours || 0).toFixed(1)}h</div>
                </div>
            </div>
            
            <h2>Revenue Summary</h2>
            <p><strong>Total Revenue:</strong> ₱${(reportsData.performance.total_revenue || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
            <p><strong>Total Orders:</strong> ${(reportsData.performance.total_orders || 0).toLocaleString()}</p>
            
            <h2>User Satisfaction</h2>
            <p><strong>Average Rating:</strong> ${reportsData.satisfaction.average || 0}/5</p>
            <p><strong>Total Ratings:</strong> ${reportsData.satisfaction.total_ratings || 0}</p>
            
            <h2>Platform Performance</h2>
            <p><strong>System Uptime:</strong> ${(reportsData.performance.uptime_percentage || 0).toFixed(1)}%</p>
            <p><strong>Average Server Load:</strong> ${(reportsData.performance.avg_server_load || 0).toFixed(1)}%</p>
            <p><strong>API Request Volume:</strong> ${(reportsData.performance.api_request_volume || 0).toLocaleString()}</p>
            
            <div class="footer">
                <p>Generated by ${platformName} Admin Dashboard - ${new Date().toLocaleString()}</p>
            </div>
        </body>
        </html>
    `);
    
    printWindow.document.close();
    printWindow.print();
}

// ============== Sellers Management ==============
// Note: renderSellersTable is defined above with expandable stores support

function filterSellers() {
    const searchTerm = document.getElementById('sellerSearch').value.toLowerCase();
    
    const filtered = sellers.filter(seller => {
        return (
            (seller.business_name && seller.business_name.toLowerCase().includes(searchTerm)) ||
            (seller.email && seller.email.toLowerCase().includes(searchTerm)) ||
            (seller.first_name && seller.first_name.toLowerCase().includes(searchTerm)) ||
            (seller.last_name && seller.last_name.toLowerCase().includes(searchTerm))
        );
    });
    
    // Temporarily replace sellers array for rendering
    const originalSellers = sellers;
    sellers = filtered;
    renderSellersTable();
    sellers = originalSellers;
}

function viewSellerDetails(sellerId) {
    // Use new action panel instead of old modal
    openSellerActionPanel(sellerId);
}

async function approveSeller() {
    if (!selectedSellerId) return;
    
    try {
        // Call API to approve seller
        const response = await authFetch(`/api/sellers/${selectedSellerId}/verify`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success || response.ok) {
            // Success - reload sellers list
            await loadSellersData();
            await loadDashboardData();
            
            // Add to activity log
            const seller = sellers.find(s => s.seller_id === selectedSellerId);
            if (seller) {
                activityLog.unshift({ 
                    type: 'approval', 
                    message: `${seller.first_name} ${seller.last_name} seller account approved and shop activated`, 
                    timestamp: Date.now(), 
                    icon: '✅' 
                });
            }
            
            // Show success message
            alert('Seller approved successfully! Their shop is now active and visible on shop.html');
            closeModal('sellerModal');
        } else {
            alert('Failed to approve seller: ' + (data.message || data.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Error approving seller:', err);
        alert('Error approving seller. Please try again.');
    }
}

function rejectSeller() {
    if (!selectedSellerId) return;
    const seller = sellers.find(s => s.seller_id === selectedSellerId);
    if (seller) {
        // TODO: Implement API call for rejection
        seller.verified = 0;
        activityLog.unshift({ type: 'rejection', message: `${seller.first_name} ${seller.last_name} seller account rejected`, timestamp: Date.now(), icon: '❌' });
        renderSellersTable();
        closeModal('sellerModal');
    }
}

async function quickApproveSeller(sellerId) {
    selectedSellerId = sellerId;
    await approveSeller();
}

function quickRejectSeller(sellerId) {
    selectedSellerId = sellerId;
    rejectSeller();
}

// ============== Riders Management ==============
function renderRidersTable() {
    const tbody = document.getElementById('ridersTableBody');
    tbody.innerHTML = '';

    let filtered = riders;

    // Apply status filter
    if (currentRiderFilter !== 'all') {
        filtered = filtered.filter(r => r.rider_status === currentRiderFilter);
    }

    // Apply search filter
    const searchTerm = document.getElementById('riderSearch')?.value.toLowerCase() || '';
    if (searchTerm) {
        filtered = filtered.filter(r => 
            (r.first_name || '').toLowerCase().includes(searchTerm) ||
            (r.last_name || '').toLowerCase().includes(searchTerm) ||
            (r.email || '').toLowerCase().includes(searchTerm)
        );
    }

    filtered.forEach(rider => {
        const row = document.createElement('tr');
        const fullName = `${rider.first_name || ''} ${rider.last_name || ''}`.trim() || 'N/A';
        const vehicleType = rider.vehicle_type || 'N/A';
        const plateNumber = rider.plate_number || 'N/A';
        const email = rider.email || 'N/A';
        const status = rider.rider_status || 'pending';
        const joinDate = rider.created_at ? new Date(rider.created_at).toLocaleDateString('en-US', {
            year: 'numeric', month: 'short', day: 'numeric'
        }) : 'N/A';
        
        const statusBadge = getStatusBadge(status);
        
        row.innerHTML = `
            <td>${rider.id}</td>
            <td><strong>${fullName}</strong></td>
            <td>${email}</td>
            <td>${vehicleType}</td>
            <td>${plateNumber}</td>
            <td>${statusBadge}</td>
            <td>${joinDate}</td>
            <td style="white-space: nowrap;">
                <button class="btn btn-sm btn-primary" onclick="viewRiderDetails(${rider.id})" 
                        title="View Details" style="padding: 6px 10px; font-size: 13px; min-width: auto; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; margin-right: 5px;">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteRider(${rider.id}, '${fullName.replace(/'/g, "\\'")}')" 
                        title="Delete Rider" style="padding: 6px 10px; font-size: 13px; min-width: auto; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding: 30px; color: #999;">No riders found</td></tr>';
    }
}

function filterRiders() {
    renderRidersTable();
}

function filterRidersByStatus(button) {
    const status = button.getAttribute('data-status');
    currentRiderFilter = status;
    
    // Update filter button states
    document.querySelectorAll('#ridersSection .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    button.classList.add('active');

    // Reload data with new filter
    loadRidersWithFilter(status);
}

// Filter riders by search term
function filterRiders() {
    loadRidersWithFilter(currentRiderFilter || 'all');
}

function viewRiderDetails(riderId) {
    // Use new action panel instead of old modal
    openRiderActionPanel(riderId);
}

async function approveRider() {
    if (!selectedRiderId) return;
    
    const rider = riders.find(r => r.id === selectedRiderId);
    if (!rider) return;
    
    if (!confirm(`Approve rider account for ${rider.first_name} ${rider.last_name}?`)) return;
    
    try {
        const response = await authFetch(`/api/admin/riders/${selectedRiderId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'active' })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification('✅ Rider approved successfully!', 'success');
            closeModal('riderModal');
            loadRidersData(); // Reload the list
        } else {
            showNotification('❌ Failed to approve rider: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (err) {
        console.error('Approve rider error:', err);
        showNotification('❌ Error approving rider', 'error');
    }
}

// Show decline rider modal
function showDeclineRiderModal() {
    const modal = document.getElementById('declineRiderModal');
    if (modal) {
        document.getElementById('declineRiderReason').value = '';
        modal.style.display = 'block';
    }
}

// Close decline rider modal
function closeDeclineRiderModal() {
    const modal = document.getElementById('declineRiderModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Confirm decline rider
async function confirmDeclineRider() {
    if (!selectedRiderId) return;
    
    const reason = document.getElementById('declineRiderReason')?.value.trim();
    if (!reason) {
        showNotification('⚠️ Please provide a reason for declining', 'warning');
        return;
    }
    
    const rider = riders.find(r => r.id === selectedRiderId);
    if (!rider) return;
    
    try {
        const response = await authFetch(`/api/admin/riders/${selectedRiderId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                status: 'declined',
                reason: reason
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification('Rider application declined', 'info');
            closeDeclineRiderModal();
            closeModal('riderModal');
            loadRidersData(); // Reload the list
        } else {
            showNotification('❌ Failed to decline rider: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (err) {
        console.error('Decline rider error:', err);
        showNotification('❌ Error declining rider', 'error');
    }
}

// Legacy function kept for compatibility
function rejectRider() {
    if (!selectedRiderId) return;
    const rider = riders.find(r => r.id === selectedRiderId);
    if (rider) {
        rider.status = 'approved';
        activityLog.unshift({ type: 'approval', message: `${rider.firstName} ${rider.lastName} rider account approved`, timestamp: Date.now(), icon: '✅' });
        updateDashboardStats();
        renderRidersTable();
        closeModal('riderModal');
    }
}

function rejectRider() {
    if (!selectedRiderId) return;
    const rider = riders.find(r => r.id === selectedRiderId);
    if (rider) {
        rider.status = 'rejected';
        activityLog.unshift({ type: 'rejection', message: `${rider.firstName} ${rider.lastName} rider account rejected`, timestamp: Date.now(), icon: '❌' });
        updateDashboardStats();
        renderRidersTable();
        closeModal('riderModal');
    }
}

function quickApproveRider(riderId) {
    selectedRiderId = riderId;
    approveRider();
}

function quickRejectRider(riderId) {
    selectedRiderId = riderId;
    rejectRider();
}

// ============== Modal Functions ==============
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        // set active container attribute and blur background
        const wrapper = document.querySelector('.admin-wrapper');
        if (wrapper) {
            wrapper.setAttribute('data-active-container', modalId);
            wrapper.classList.add('blurred');
        }

        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';

        const wrapper = document.querySelector('.admin-wrapper');
        if (wrapper) {
            wrapper.removeAttribute('data-active-container');
            wrapper.classList.remove('blurred');
        }
    }
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
        document.body.style.overflow = 'auto';
        const wrapper = document.querySelector('.admin-wrapper');
        if (wrapper) {
            wrapper.removeAttribute('data-active-container');
            wrapper.classList.remove('blurred');
        }
    }
};

// ============== Print Modal to PDF ==============
function printModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    // Get modal content (the .modal-content element)
    const content = modal.querySelector('.modal-content');
    if (!content) return;

    // Open a new window and write printable content
    const printWindow = window.open('', '_blank', 'width=900,height=700');
    if (!printWindow) {
        alert('Popup blocked. Please allow popups for printing.');
        return;
    }

    const doc = printWindow.document;
    doc.open();
    doc.write('<!doctype html><html><head><meta charset="utf-8"><title>Print</title>');
    doc.write('<link rel="stylesheet" href="admin_dashboard.css">');
    doc.write('<style>body{padding:20px;font-family:Arial,Helvetica,sans-serif} .modal-content{box-shadow:none;border-radius:0;padding:0} .modal-info-row{border-bottom:1px solid #eee;padding:8px 0} </style>');
    doc.write('</head><body>');
    doc.write(content.innerHTML);
    doc.write('</body></html>');
    doc.close();

    // Give browser a moment to render, then call print
    printWindow.focus();
    setTimeout(() => {
        printWindow.print();
        // Optionally close after printing; leave open so user can save manually if needed
        // printWindow.close();
    }, 300);
}

function printReport() {
    const section = document.getElementById('reportsSection');
    if (!section) return;
    const printWindow = window.open('', '_blank', 'width=1100,height=800');
    if (!printWindow) {
        alert('Popup blocked. Please allow popups for printing.');
        return;
    }
    const doc = printWindow.document;
    doc.open();
    doc.write('<!doctype html><html><head><meta charset="utf-8"><title>Reports</title>');
    doc.write('<link rel="stylesheet" href="admin_dashboard.css">');
    doc.write('<style>body{padding:20px;font-family:Arial,Helvetica,sans-serif} .report-card-large{box-shadow:none} </style>');
    doc.write('</head><body>');
    // clone the section so we don't remove event handlers in the main page
    doc.write(section.innerHTML);
    doc.write('</body></html>');
    doc.close();
    printWindow.focus();
    setTimeout(() => { printWindow.print(); }, 300);
}

// ============== Utility Functions ==============
function capitalizeText(str) {
    return str.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function capitalizeStatus(status) {
    return status.charAt(0).toUpperCase() + status.slice(1);
}

function capitalizeCategory(category) {
    const categories = {
        'food': 'Food & Beverages',
        'apparel': 'Apparel & Fashion',
        'tools': 'Tools & Hardware',
        'equipment': 'Equipment',
        'electronics': 'Electronics',
        'home': 'Home & Garden',
        'beauty': 'Beauty & Personal Care',
        'sports': 'Sports & Outdoors',
        'other': 'Other'
    };
    return categories[category] || category;
}

function capitalizeVehicleType(type) {
    const types = {
        'motorcycle': 'Motorcycle',
        'bicycle': 'Bicycle',
        'car': 'Car',
        'van': 'Van',
        'truck': 'Truck'
    };
    return types[type] || type;
}

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-PH', options);
}

function updateFilterButtons(type, status) {
    const selector = type === 'seller' ? '.seller-filters' : '.rider-filters';
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
}

function downloadFile(filename) {
    console.log('Downloading:', filename);
    alert('File download initiated for: ' + filename);
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        alert('Logged out successfully');
        window.location.href = 'loginregister.html';
    }
}

// ============== Platform Settings ==============
async function loadPlatformSettings() {
    try {
        // Load admin account info (email, last login)
        try {
            const userResponse = await authFetch('/api/me');
            if (userResponse.ok) {
                const userResult = await userResponse.json();
                if (userResult.success && userResult.data) {
                    const user = userResult.data;
                    
                    // Update admin email
                    const emailInput = document.getElementById('adminEmail');
                    if (emailInput) {
                        emailInput.value = user.email || '';
                    }
                    
                    // Update last login
                    const lastLoginInput = document.getElementById('lastLogin');
                    if (lastLoginInput) {
                        const lastLogin = user.last_login;
                        if (lastLogin) {
                            const loginDate = new Date(lastLogin);
                            const formatted = formatLastLogin(loginDate);
                            lastLoginInput.value = formatted;
                        } else {
                            lastLoginInput.value = 'Never';
                        }
                    }
                }
            }
        } catch (userErr) {
            console.warn('Could not load user info:', userErr);
        }
        
        // Load platform settings
        const response = await authFetch('/api/admin/platform-settings');
        if (!response.ok) {
            throw new Error('Failed to load settings');
        }
        
        const result = await response.json();
        if (result.success && result.data) {
            const settings = result.data;
            
            // Populate form fields
            if (settings.platform_name) {
                document.getElementById('platformName').value = settings.platform_name.value || 'Hub';
            }
            if (settings.default_commission) {
                document.getElementById('defaultCommission').value = settings.default_commission.value || '10';
            }
            if (settings.rider_service_fee) {
                document.getElementById('riderServiceFee').value = settings.rider_service_fee.value || '5';
            }
            if (settings.seller_approval_required) {
                document.getElementById('sellerApprovalRequired').value = settings.seller_approval_required.value || '1';
            }
        }
    } catch (error) {
        console.error('Error loading platform settings:', error);
    }
}

function formatLastLogin(date) {
    if (!date || isNaN(date.getTime())) {
        return 'Never';
    }
    
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
        timeZoneName: 'short'
    };
    
    return date.toLocaleString('en-US', options);
}

async function saveSettings() {
    try {
        const platformName = document.getElementById('platformName').value.trim();
        const defaultCommission = parseFloat(document.getElementById('defaultCommission').value);
        const riderServiceFee = parseFloat(document.getElementById('riderServiceFee').value);
        const sellerApprovalRequired = document.getElementById('sellerApprovalRequired').value;
        
        // Validation
        if (!platformName) {
            showNotification('Platform name cannot be empty', 'error');
            return;
        }
        
        if (isNaN(defaultCommission) || defaultCommission < 0 || defaultCommission > 100) {
            showNotification('Default Commission must be a number between 0 and 100', 'error');
            return;
        }
        
        if (isNaN(riderServiceFee) || riderServiceFee < 0 || riderServiceFee > 100) {
            showNotification('Rider Service Fee must be a number between 0 and 100', 'error');
            return;
        }
        
        const settingsData = {
            platform_name: { value: platformName },
            default_commission: { value: String(defaultCommission) },
            rider_service_fee: { value: String(riderServiceFee) },
            seller_approval_required: { value: sellerApprovalRequired }
        };
        
        const response = await authFetch('/api/admin/platform-settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settingsData)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Failed to save settings');
        }
        
        const result = await response.json();
        if (result.success) {
            showNotification('Settings saved successfully!', 'success');
            // Update platform name throughout the app
            updatePlatformName(platformName);
            // Reload settings to show updated values
            setTimeout(() => loadPlatformSettings(), 500);
        } else {
            throw new Error(result.message || 'Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Error saving settings: ' + error.message, 'error');
    }
}

function showNotification(message, type) {
    // Use existing notification system if available
    if (window.notify) {
        if (type === 'success') {
            window.notify.success(message);
        } else {
            window.notify.error(message);
        }
    } else {
        // Fallback to alert
        alert(message);
    }
}

async function cancelSettings() {
    // Reload settings from server
    await loadPlatformSettings();
}

// Update platform name throughout the application
function updatePlatformName(platformName) {
    // Update page title
    document.title = document.title.replace(/^[^-]+/, platformName);
    
    // Update navbar logos
    document.querySelectorAll('.logo a, .sidebar-brand .brand-text').forEach(el => {
        if (el.textContent.trim() === 'Hub' || el.textContent.trim() === 'Admin Panel') {
            el.textContent = platformName;
        }
    });
    
    // Store in localStorage for other pages
    localStorage.setItem('platform_name', platformName);
}

// ============== Admin Return/Refund Requests ==============
let adminReturnRequests = [];
let currentAdminReturnFilter = 'all';

async function loadAdminReturnRequests() {
    try {
        const response = await authFetch('/api/admin/return-refund-requests');
        if (!response.ok) throw new Error('Failed to load return/refund requests');

        const data = await response.json();
        adminReturnRequests = data.data?.requests || data.requests || [];
        
        // Debug: Log full request data to check all status fields
        console.log('Admin return requests loaded (full data):', adminReturnRequests);
        console.log('Admin return requests summary:', adminReturnRequests.map(r => ({
            id: r.id,
            status: r.status,
            seller_response: r.seller_response,
            pickup_rider_id: r.pickup_rider_id,
            pickup_completed_at: r.pickup_completed_at,
            item_received_at: r.item_received_at,
            refund_processed_at: r.refund_processed_at,
            request_type: r.request_type,
            formatted_status: formatAdminReturnStatus(r)
        })));
        
        // Fix: Update status for any requests where item_received_at exists but status is still 'approved'
        // This handles cases where the backend update didn't work correctly
        adminReturnRequests.forEach(req => {
            if (req.item_received_at && req.status === 'approved') {
                console.warn(`[loadAdminReturnRequests] Fixing status for request #${req.id}: item_received_at exists but status is 'approved'`);
                req.status = 'processing';
            }
        });
        
        // Update badge count
        const processingCount = adminReturnRequests.filter(r => r.status === 'processing' && !r.refund_processed_at).length;
        const badge = document.getElementById('pendingRefundsBadge');
        if (badge) {
            if (processingCount > 0) {
                badge.textContent = processingCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
        
        renderAdminReturnRequests(adminReturnRequests);
    } catch (error) {
        console.error('Error loading admin return requests:', error);
        const tbody = document.getElementById('adminReturnRequestsTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" style="text-align: center; padding: 40px; color: #ef4444;">
                        <i class="fa-solid fa-exclamation-circle" style="font-size: 48px; margin-bottom: 16px;"></i>
                        <p>Failed to load return/refund requests. Please try again later.</p>
                    </td>
                </tr>
            `;
        }
    }
}

function filterAdminReturnRequests(filter) {
    currentAdminReturnFilter = filter;
    
    // Update filter buttons
    document.querySelectorAll('#returnsSection .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event?.target?.classList.add('active');
    
    let filtered = adminReturnRequests;
    if (filter !== 'all') {
        if (filter === 'processing') {
            filtered = adminReturnRequests.filter(r => r.status === 'processing');
        } else if (filter === 'pending') {
            filtered = adminReturnRequests.filter(r => r.status === 'pending' || r.seller_response === 'pending');
        } else if (filter === 'approved') {
            filtered = adminReturnRequests.filter(r => r.seller_response === 'approved' && r.status !== 'completed' && r.status !== 'rejected');
        } else if (filter === 'completed') {
            filtered = adminReturnRequests.filter(r => r.status === 'completed');
        } else if (filter === 'rejected') {
            filtered = adminReturnRequests.filter(r => r.status === 'rejected' || r.seller_response === 'rejected');
        }
    }
    
    renderAdminReturnRequests(filtered);
}

function renderAdminReturnRequests(requests) {
    const tbody = document.getElementById('adminReturnRequestsTableBody');
    if (!tbody) return;

    if (requests.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 40px;">
                    <i class="fa-solid fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                    <p style="color: #666;">No return/refund requests found.</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = requests.map(req => {
        const statusText = formatAdminReturnStatus(req);
        const statusColor = getAdminReturnStatusColor(req);
        const createdDate = new Date(req.created_at);
        const refundAmount = parseFloat(req.subtotal || 0).toFixed(2);
        
        // Debug: Log what status is being rendered
        console.log(`[renderAdminReturnRequests] Request #${req.id}: Rendering with statusText="${statusText}", status="${req.status}", item_received_at="${req.item_received_at}"`);
        
        // Check if can process refund
        // Can process if: status is processing, seller approved, and for returns - item must be received
        const canProcessRefund = req.status === 'processing' && 
                                  req.seller_response === 'approved' &&
                                  (!req.request_type || req.request_type === 'refund' || req.item_received_at);
        
        return `
            <tr>
                <td>#${req.id}</td>
                <td>#${req.order_id}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${req.product_image ? `
                            <img src="${req.product_image.startsWith('http') ? req.product_image : 'http://127.0.0.1:5000' + req.product_image}" 
                                 style="width: 40px; height: 40px; object-fit: cover; border-radius: 6px;" 
                                 onerror="this.src='https://via.placeholder.com/40'">
                        ` : ''}
                        <span>${req.product_name || 'Product'}</span>
                    </div>
                </td>
                <td>${req.customer_name || (req.customer_first_name && req.customer_last_name ? `${req.customer_first_name} ${req.customer_last_name}` : 'Customer')}</td>
                <td>${req.seller_name || 'Seller'}</td>
                <td><span style="text-transform: capitalize;">${req.request_type || 'return'}</span></td>
                <td>₱${refundAmount}</td>
                <td>
                    <span class="status-badge" style="background: ${statusColor}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;" data-request-id="${req.id}" data-status-text="${statusText}">
                        ${statusText}
                    </span>
                </td>
                <td>${createdDate.toLocaleDateString()}</td>
                <td>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button onclick="viewAdminReturnRequestDetails(${req.id})" 
                                style="padding: 6px 12px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
                            View Details
                        </button>
                        ${req.seller_response === 'pending' || !req.seller_response ? `
                            <button onclick="adminApproveReturnRequest(${req.id})" 
                                    style="padding: 6px 12px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
                                Approve
                            </button>
                            <button onclick="adminRejectReturnRequest(${req.id})" 
                                    style="padding: 6px 12px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
                                Reject
                            </button>
                        ` : ''}
                        ${canProcessRefund ? `
                            <button onclick="processRefund(${req.id})" 
                                    style="padding: 6px 12px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">
                                Process Refund
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function formatAdminReturnStatus(request) {
    // Debug: Log the request object to see what we're working with
    if (request.id) {
        console.log(`[formatAdminReturnStatus] Request #${request.id}:`, {
            status: request.status,
            seller_response: request.seller_response,
            pickup_rider_id: request.pickup_rider_id,
            pickup_completed_at: request.pickup_completed_at,
            item_received_at: request.item_received_at,
            refund_processed_at: request.refund_processed_at,
            request_type: request.request_type
        });
    }
    
    // Priority order: Check most advanced stages first
    
    // 1. Check for completed refund first - highest priority
    const hasRefundProcessed = request.refund_processed_at && 
                                request.refund_processed_at !== null && 
                                request.refund_processed_at !== '' &&
                                request.refund_processed_at !== 'None' &&
                                request.refund_processed_at !== undefined;
    
    if (hasRefundProcessed || request.status === 'completed') {
        console.log(`[formatAdminReturnStatus] Request #${request.id}: Returning "Refund Completed"`);
        return 'Refund Completed';
    }
    
    // 2. Check if seller has confirmed receipt (item_received_at exists)
    // This means the item is back with seller and ready for refund processing
    // IMPORTANT: Check this BEFORE checking pickup_rider_id to avoid showing "Pickup Scheduled" when item is already received
    const hasItemReceived = request.item_received_at && 
                            request.item_received_at !== null && 
                            request.item_received_at !== '' &&
                            request.item_received_at !== 'None' &&
                            request.item_received_at !== undefined;
    
    if (hasItemReceived) {
        // If admin has approved after item received, status should be "Approved - Refund Ready"
        if (request.status === 'processing' || (request.seller_response === 'approved' && request.status === 'approved')) {
            console.log(`[formatAdminReturnStatus] Request #${request.id}: Item received and approved, returning "Approved - Refund Ready"`);
            return 'Approved - Refund Ready';
        }
        console.log(`[formatAdminReturnStatus] Request #${request.id}: Item received, returning "Item Received - Ready for Refund"`);
        return 'Item Received - Ready for Refund';
    }
    
    // 3. Check status field
    if (request.status === 'processing') {
        if (request.request_type === 'return' || request.request_type === 'both') {
            // Status is processing but item_received_at not set - rider delivered, waiting for seller confirmation
            console.log(`[formatAdminReturnStatus] Request #${request.id}: Status processing, returning "Item Delivered - Awaiting Seller Confirmation"`);
            return 'Item Delivered - Awaiting Seller Confirmation';
        }
        console.log(`[formatAdminReturnStatus] Request #${request.id}: Status processing (refund-only), returning "Refund Processing"`);
        return 'Refund Processing';
    } else if (request.status === 'approved' || request.seller_response === 'approved') {
        if (request.request_type === 'return' || request.request_type === 'both') {
            // Approved status - check progress in order of completion
            // Check if item was picked up but not yet delivered
            const hasPickupCompleted = request.pickup_completed_at && 
                                       request.pickup_completed_at !== null && 
                                       request.pickup_completed_at !== '' &&
                                       request.pickup_completed_at !== 'None';
            
            if (hasPickupCompleted && !hasItemReceived) {
                console.log(`[formatAdminReturnStatus] Request #${request.id}: Pickup completed, returning "Item Picked Up - Returning to Seller"`);
                return 'Item Picked Up - Returning to Seller';
            } 
            // Check if rider is assigned but hasn't picked up yet
            else if (request.pickup_rider_id && !hasPickupCompleted) {
                console.log(`[formatAdminReturnStatus] Request #${request.id}: Rider assigned but not picked up, returning "Pickup Scheduled - Rider Assigned"`);
                return 'Pickup Scheduled - Rider Assigned';
            }
            // Just approved, waiting for rider
            console.log(`[formatAdminReturnStatus] Request #${request.id}: Approved, waiting for rider, returning "Approved - Awaiting Rider Pickup"`);
            return 'Approved - Awaiting Rider Pickup';
        } else {
            // Refund-only request (no return needed)
            console.log(`[formatAdminReturnStatus] Request #${request.id}: Approved refund-only, returning "Approved - Ready for Refund"`);
            return 'Approved - Ready for Refund';
        }
    } else if (request.seller_response === 'rejected' || request.status === 'rejected') {
        console.log(`[formatAdminReturnStatus] Request #${request.id}: Rejected, returning "Rejected"`);
        return 'Rejected';
    } else if (request.seller_response === 'request_info') {
        console.log(`[formatAdminReturnStatus] Request #${request.id}: More info requested, returning "More Info Requested"`);
        return 'More Info Requested';
    }
    console.log(`[formatAdminReturnStatus] Request #${request.id}: Default, returning "Pending Review"`);
    return 'Pending Review';
}

function getAdminReturnStatusColor(request) {
    if (request.status === 'completed') return '#10b981';
    if (request.status === 'processing') return '#f59e0b';
    if (request.status === 'approved' || request.seller_response === 'approved') return '#3b82f6';
    if (request.seller_response === 'rejected') return '#ef4444';
    if (request.seller_response === 'request_info') return '#ff9800';
    return '#6c757d';
}

async function viewAdminReturnRequestDetails(requestId) {
    const request = adminReturnRequests.find(r => r.id === requestId);
    if (!request) {
        // Try to fetch from server
        try {
            const response = await authFetch(`/api/admin/return-refund-requests`);
            if (response.ok) {
                const data = await response.json();
                const requests = data.data?.requests || data.requests || [];
                const found = requests.find(r => r.id === requestId);
                if (found) {
                    showAdminReturnRequestModal(found);
                    return;
                }
            }
        } catch (err) {
            console.error('Error fetching request:', err);
        }
        
        if (window.notify) {
            window.notify.error('Request not found');
        } else {
            alert('Request not found');
        }
        return;
    }
    
    showAdminReturnRequestModal(request);
}

function showAdminReturnRequestModal(request) {
    // Remove existing modal if any
    const existingModal = document.getElementById('adminReturnRequestModal');
    if (existingModal) existingModal.remove();

    const statusColor = getAdminReturnStatusColor(request);
    const statusText = formatAdminReturnStatus(request);
    const requestTypeIcon = request.request_type === 'return' ? 'fa-rotate-left' : request.request_type === 'refund' ? 'fa-money-bill-wave' : 'fa-exchange-alt';
    const requestTypeColor = request.request_type === 'return' ? '#17a2b8' : request.request_type === 'refund' ? '#28a745' : '#ff9800';
    
    const modalHTML = `
        <div id="adminReturnRequestModal" class="modal" style="display: block;">
            <div class="modal-content modal-large modern-modal">
                <div class="modal-header-modern">
                    <div class="modal-header-content">
                        <i class="fa-solid fa-rotate-left" aria-hidden="true" style="font-size: 24px; color: var(--white);"></i>
                        <div>
                            <h2>Return/Refund Request Details</h2>
                            <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9; font-weight: 400;">Request ID: #${request.id} • Order #${request.order_id}</p>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <button onclick="refreshAdminReturnRequest(${request.id})" class="modal-close-modern" style="width: 36px; height: 36px; border-radius: 8px; background: rgba(255,255,255,0.15); display: flex; align-items: center; justify-content: center; font-size: 16px; padding: 0;" title="Refresh" aria-label="Refresh">
                            <i class="fa-solid fa-rotate"></i>
                        </button>
                        <button class="modal-close-modern" aria-label="Close" onclick="closeAdminReturnRequestModal()">&times;</button>
                    </div>
                </div>
                <div class="modal-body-modern simple-modal">
                    <!-- Status Card -->
                    <div class="form-section-card">
                        <div class="form-section-header">
                            <i class="fa fa-info-circle"></i>
                            <h4>Request Status</h4>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: space-between; padding: 16px; background: linear-gradient(135deg, ${statusColor}15 0%, ${statusColor}08 100%); border-left: 4px solid ${statusColor}; border-radius: 8px;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 12px; height: 12px; border-radius: 50%; background: ${statusColor}; box-shadow: 0 0 0 4px ${statusColor}30;"></div>
                                <div>
                                    <div style="color: #666; font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Current Status</div>
                                    <div style="color: ${statusColor}; font-size: 18px; font-weight: 600; margin-top: 4px;">${statusText}</div>
                                </div>
                            </div>
                            <div style="padding: 8px 16px; background: ${statusColor}; color: white; border-radius: 20px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                ${request.request_type.charAt(0).toUpperCase() + request.request_type.slice(1)}
                            </div>
                        </div>
                    </div>

                    <!-- Product Information -->
                    <div class="form-section-card">
                        <div class="form-section-header">
                            <i class="fa fa-box"></i>
                            <h4>Product Information</h4>
                        </div>
                        <div style="display: flex; align-items: center; gap: 16px;">
                            ${request.product_image ? `
                                <img src="${request.product_image.startsWith('http') ? request.product_image : 'http://127.0.0.1:5000' + request.product_image}" 
                                     style="width: 100px; height: 100px; object-fit: cover; border-radius: 12px; border: 2px solid #e0e0e0;" 
                                     onerror="this.src='https://via.placeholder.com/100'">
                            ` : `
                                <div style="width: 100px; height: 100px; background: linear-gradient(135deg, var(--primary-color) 0%, #2980b9 100%); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                                    <i class="fa-solid fa-box" style="font-size: 40px; color: white;"></i>
                                </div>
                            `}
                            <div style="flex: 1;">
                                <h3 style="margin: 0 0 8px 0; color: var(--text-color); font-size: 20px; font-weight: 600;">${request.product_name || 'Product Name'}</h3>
                                <div style="display: flex; align-items: center; gap: 6px; color: #666; font-size: 14px;">
                                    <i class="fa-solid ${requestTypeIcon}" style="color: ${requestTypeColor};"></i>
                                    <span style="font-weight: 500;">${request.request_type.charAt(0).toUpperCase() + request.request_type.slice(1)} Request</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Customer Information -->
                    <div class="form-section-card">
                        <div class="form-section-header">
                            <i class="fa fa-user"></i>
                            <h4>Customer Information</h4>
                        </div>
                        <div style="font-size: 18px; font-weight: 600; color: var(--text-color); margin-bottom: 16px;">
                            ${request.customer_name || (request.customer_first_name && request.customer_last_name ? `${request.customer_first_name} ${request.customer_last_name}` : 'Customer')}
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            ${request.customer_phone ? `
                                <div style="display: flex; align-items: center; gap: 10px; color: var(--text-light); font-size: 14px;">
                                    <i class="fa-solid fa-phone" style="color: var(--primary-color); width: 20px;"></i>
                                    <span>${request.customer_phone}</span>
                                </div>
                            ` : ''}
                            ${request.customer_email ? `
                                <div style="display: flex; align-items: center; gap: 10px; color: var(--text-light); font-size: 14px;">
                                    <i class="fa-solid fa-envelope" style="color: var(--primary-color); width: 20px;"></i>
                                    <span>${request.customer_email}</span>
                                </div>
                            ` : ''}
                            ${request.customer_address ? `
                                <div style="display: flex; align-items: start; gap: 10px; color: var(--text-light); font-size: 14px;">
                                    <i class="fa-solid fa-map-marker-alt" style="color: var(--primary-color); width: 20px; margin-top: 2px;"></i>
                                    <span>${request.customer_address}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    <!-- Seller Information -->
                    <div class="form-section-card">
                        <div class="form-section-header">
                            <i class="fa fa-store"></i>
                            <h4>Seller Information</h4>
                        </div>
                        <div style="font-size: 16px; font-weight: 600; color: var(--text-color);">
                            ${request.seller_name || 'Unknown Seller'}
                        </div>
                    </div>

                    <!-- Reason -->
                    <div class="form-section-card" style="border-left: 4px solid #ffc107;">
                        <div class="form-section-header">
                            <i class="fa fa-comment-dots"></i>
                            <h4>Reason for Request</h4>
                        </div>
                        <div style="padding: 16px; background: #fff3cd; border-radius: 8px; color: var(--text-color); font-size: 15px; line-height: 1.6; white-space: pre-wrap;">${request.reason || 'No reason provided'}</div>
                    </div>

                    <!-- Evidence Images -->
                    ${request.evidence_images && request.evidence_images.length > 0 ? `
                        <div class="form-section-card">
                            <div class="form-section-header">
                                <i class="fa fa-images"></i>
                                <h4>Evidence Images</h4>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px;">
                                ${request.evidence_images.map(img => `
                                    <div style="position: relative; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.3s;" 
                                         onmouseover="this.style.transform='scale(1.05)'" 
                                         onmouseout="this.style.transform='scale(1)'"
                                         onclick="window.open('${img.startsWith('http') ? img : 'http://127.0.0.1:5000' + img}', '_blank')">
                                        <img src="${img.startsWith('http') ? img : 'http://127.0.0.1:5000' + img}" 
                                             style="width: 100%; height: 120px; object-fit: cover; display: block;"
                                             onerror="this.src='https://via.placeholder.com/120'">
                                        <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.6); color: white; border-radius: 6px; padding: 4px 8px; font-size: 11px;">
                                            <i class="fa-solid fa-expand"></i>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Rejection Reason -->
                    ${request.rejection_reason ? `
                        <div class="form-section-card" style="border-left: 4px solid #dc3545; background: #f8d7da;">
                            <div class="form-section-header">
                                <i class="fa fa-exclamation-triangle"></i>
                                <h4>Rejection Reason</h4>
                            </div>
                            <div style="padding: 16px; background: white; border-radius: 8px; color: #721c24; font-size: 15px; line-height: 1.6;">${request.rejection_reason}</div>
                        </div>
                    ` : ''}

                    <!-- Timeline -->
                    <div class="form-section-card">
                        <div class="form-section-header">
                            <i class="fa fa-clock-rotate-left"></i>
                            <h4>Request Timeline</h4>
                        </div>
                        <div style="position: relative; padding-left: 30px;">
                            <div style="position: absolute; left: 8px; top: 0; bottom: 0; width: 2px; background: linear-gradient(180deg, #28a745 0%, #17a2b8 50%, #ffc107 100%);"></div>
                            
                            <div style="position: relative; margin-bottom: 20px;">
                                <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #28a745; border: 3px solid white; box-shadow: 0 0 0 2px #28a745;"></div>
                                <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                    <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Request Submitted</div>
                                    <div style="color: var(--text-light); font-size: 13px;">${new Date(request.created_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                </div>
                            </div>

                            ${request.pickup_scheduled_at ? `
                                <div style="position: relative; margin-bottom: 20px;">
                                    <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #17a2b8; border: 3px solid white; box-shadow: 0 0 0 2px #17a2b8;"></div>
                                    <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Pickup Scheduled</div>
                                        <div style="color: var(--text-light); font-size: 13px;">${new Date(request.pickup_scheduled_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${request.pickup_completed_at ? `
                                <div style="position: relative; margin-bottom: 20px;">
                                    <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #28a745; border: 3px solid white; box-shadow: 0 0 0 2px #28a745;"></div>
                                    <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Pickup Completed</div>
                                        <div style="color: var(--text-light); font-size: 13px;">${new Date(request.pickup_completed_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${request.item_received_at ? `
                                <div style="position: relative; margin-bottom: 20px;">
                                    <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #28a745; border: 3px solid white; box-shadow: 0 0 0 2px #28a745;"></div>
                                    <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Item Received by Seller</div>
                                        <div style="color: var(--text-light); font-size: 13px;">${new Date(request.item_received_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    </div>
                                </div>
                            ` : ''}
                            
                            ${request.refund_processed_at ? `
                                <div style="position: relative; margin-bottom: 20px;">
                                    <div style="position: absolute; left: -22px; width: 16px; height: 16px; border-radius: 50%; background: #28a745; border: 3px solid white; box-shadow: 0 0 0 2px #28a745;"></div>
                                    <div style="background: #f8f9fa; border-radius: 10px; padding: 14px 16px; border: 1px solid #e9ecef;">
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Coupon Issued</div>
                                        <div style="color: var(--text-light); font-size: 13px; margin-bottom: 8px;">${new Date(request.refund_processed_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                        ${request.admin_notes && request.admin_notes.includes('Coupon Code:') ? `
                                            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 12px; border-radius: 8px; margin-top: 8px;">
                                                <div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">Coupon Code</div>
                                                <div style="font-size: 20px; font-weight: 700; letter-spacing: 2px; font-family: 'Courier New', monospace;">${request.admin_notes.match(/Coupon Code:\s*([A-Z0-9]+)/)?.[1] || 'N/A'}</div>
                                            </div>
                                        ` : ''}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                ${request.seller_response === 'pending' || !request.seller_response || (request.status === 'processing' && request.seller_response === 'approved' && !request.refund_processed_at) ? `
                    <div class="modal-actions-modern">
                        ${request.seller_response === 'pending' || !request.seller_response ? `
                            <button class="btn btn-cancel-modern" onclick="closeAdminReturnRequestModal()">
                                <i class="fa fa-times"></i> Close
                            </button>
                            <button class="btn btn-save-modern" style="background: #10b981;" onclick="adminApproveReturnRequest(${request.id})">
                                <i class="fa fa-check"></i> Approve
                            </button>
                            <button class="btn" style="background: #ef4444; color: white; padding: 10px 22px; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; box-shadow: 0 6px 12px rgba(239, 68, 68, 0.3);" onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 8px 16px rgba(239, 68, 68, 0.35)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 6px 12px rgba(239, 68, 68, 0.3)'" onclick="adminRejectReturnRequest(${request.id})">
                                <i class="fa fa-times"></i> Reject
                            </button>
                        ` : request.status === 'processing' && request.seller_response === 'approved' && !request.refund_processed_at && (!request.request_type || request.request_type === 'refund' || request.item_received_at) ? `
                            <button class="btn btn-cancel-modern" onclick="closeAdminReturnRequestModal()">
                                <i class="fa fa-times"></i> Close
                            </button>
                            <button class="btn btn-save-modern" style="background: #10b981;" onclick="processRefund(${request.id})">
                                <i class="fa fa-money-bill-wave"></i> Process Refund
                            </button>
                        ` : ''}
                    </div>
                ` : `
                    <div class="modal-actions-modern">
                        <button class="btn btn-cancel-modern" onclick="closeAdminReturnRequestModal()">
                            <i class="fa fa-times"></i> Close
                        </button>
                    </div>
                `}
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeAdminReturnRequestModal() {
    const modal = document.getElementById('adminReturnRequestModal');
    if (modal) {
        modal.style.display = 'none';
        setTimeout(() => modal.remove(), 300);
    }
}

async function refreshAdminReturnRequest(requestId) {
    try {
        const response = await authFetch(`/api/admin/return-refund-requests`);
        if (!response.ok) throw new Error('Failed to refresh request');

        const data = await response.json();
        const requests = data.data?.requests || data.requests || [];
        const request = requests.find(r => r.id === requestId);
        
        if (request) {
            showAdminReturnRequestModal(request);
            if (window.notify) {
                window.notify.success('Request details refreshed');
            }
        } else {
            if (window.notify) {
                window.notify.error('Request not found');
            }
        }
    } catch (error) {
        console.error('Error refreshing request:', error);
        if (window.notify) {
            window.notify.error('Failed to refresh request details');
        }
    }
}

function downloadEvidenceImages(requestId) {
    const request = adminReturnRequests.find(r => r.id === requestId);
    if (!request || !request.evidence_images || request.evidence_images.length === 0) {
        if (window.notify) {
            window.notify.warning('No evidence images to download');
        }
        return;
    }
    
    // Open each image in a new tab for download
    request.evidence_images.forEach((img, idx) => {
        const link = document.createElement('a');
        link.href = img.startsWith('http') ? img : 'http://127.0.0.1:5000' + img;
        link.download = `evidence_${requestId}_${idx + 1}.jpg`;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
    
    if (window.notify) {
        window.notify.success(`Downloading ${request.evidence_images.length} evidence image(s)...`);
    }
}

function openMapForAddress(address) {
    const encodedAddress = encodeURIComponent(address);
    window.open(`https://www.google.com/maps/search/?api=1&query=${encodedAddress}`, '_blank');
}

async function adminApproveReturnRequest(requestId) {
    if (!confirm('Are you sure you want to approve this return/refund request?')) {
        return;
    }
    
    try {
        // Admin can override seller response by calling the seller respond endpoint
        // Or we can create a separate admin endpoint
        const response = await authFetch(`/api/admin/return-refund-requests/${requestId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Failed to approve request');
        }
        
        const result = await response.json();
        if (result.success) {
            if (window.notify) {
                window.notify.success('Request approved successfully!');
            } else {
                alert('Request approved successfully!');
            }
            closeAdminReturnRequestModal();
            await loadAdminReturnRequests();
        } else {
            throw new Error(result.message || 'Failed to approve request');
        }
    } catch (error) {
        console.error('Error approving request:', error);
        if (window.notify) {
            window.notify.error('Error approving request: ' + error.message);
        } else {
            alert('Error approving request: ' + error.message);
        }
    }
}

async function adminRejectReturnRequest(requestId) {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason || !reason.trim()) {
        if (window.notify) {
            window.notify.error('Rejection reason is required');
        } else {
            alert('Rejection reason is required');
        }
        return;
    }
    
    try {
        const response = await authFetch(`/api/admin/return-refund-requests/${requestId}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rejection_reason: reason.trim()
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Failed to reject request');
        }
        
        const result = await response.json();
        if (result.success) {
            if (window.notify) {
                window.notify.success('Request rejected successfully!');
            } else {
                alert('Request rejected successfully!');
            }
            closeAdminReturnRequestModal();
            await loadAdminReturnRequests();
        } else {
            throw new Error(result.message || 'Failed to reject request');
        }
    } catch (error) {
        console.error('Error rejecting request:', error);
        if (window.notify) {
            window.notify.error('Error rejecting request: ' + error.message);
        } else {
            alert('Error rejecting request: ' + error.message);
        }
    }
}

async function processRefund(requestId) {
    if (!confirm('Are you sure you want to process this refund? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await authFetch(`/api/admin/return-refund-requests/${requestId}/process-refund`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Failed to process refund');
        }
        
        const result = await response.json();
        if (result.success) {
            const couponCode = result.data?.coupon_code || result.coupon_code;
            const couponAmount = result.data?.coupon_amount || result.coupon_amount;
            
            let message = result.message || 'Refund processed successfully!';
            if (couponCode) {
                message = `Coupon Code: ${couponCode}\nAmount: ₱${parseFloat(couponAmount || 0).toFixed(2)}\n\n${message}`;
            }
            
            if (window.notify) {
                window.notify.success(message);
            } else {
                alert(message);
            }
            
            // Close modal first
            closeAdminReturnRequestModal();
            
            // Reload requests to get updated data
            await loadAdminReturnRequests();
            
            // If modal was showing this request, refresh it with new data
            const updatedRequests = adminReturnRequests;
            const updatedRequest = updatedRequests.find(r => r.id === requestId);
            if (updatedRequest) {
                console.log('Updated request after refund processing:', updatedRequest);
            }
        } else {
            throw new Error(result.message || 'Failed to process refund');
        }
    } catch (error) {
        console.error('Error processing refund:', error);
        if (window.notify) {
            window.notify.error('Error processing refund: ' + error.message);
        } else {
            alert('Error processing refund: ' + error.message);
        }
    }
}

// ============== Helper Functions ==============
function capitalizeText(text) {
    if (!text) return 'N/A';
    return text.charAt(0).toUpperCase() + text.slice(1);
}

let chartInstances = {};

function destroyChart(chartId) {
    if (chartInstances[chartId]) {
        chartInstances[chartId].destroy();
    }
}

function initializeDashboardCharts() {
    // User Growth Chart
    destroyChart('userGrowthChart');
    const userGrowthCtx = document.getElementById('userGrowthChart');
    if (userGrowthCtx) {
        chartInstances['userGrowthChart'] = new Chart(userGrowthCtx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Sellers',
                    data: [sellers.length * 0.25, sellers.length * 0.5, sellers.length * 0.75, sellers.length],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Riders',
                    data: [riders.length * 0.25, riders.length * 0.5, riders.length * 0.75, riders.length],
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'top' } }
            }
        });
    }
}

function initializeReportCharts() {
    // Orders by Status Chart
    destroyChart('orderStatusChart');
    const statusCtx = document.getElementById('orderStatusChart');
    if (statusCtx) {
        const statusCounts = {
            placed: orders.filter(o => o.status === 'placed').length,
            dispatched: orders.filter(o => o.status === 'dispatched').length,
            delivered: orders.filter(o => o.status === 'delivered').length,
            cancelled: orders.filter(o => o.status === 'cancelled').length
        };
        
        chartInstances['orderStatusChart'] = new Chart(statusCtx, {
            type: 'pie',
            data: {
                labels: ['Placed', 'Dispatched', 'Delivered', 'Cancelled'],
                datasets: [{
                    data: [statusCounts.placed, statusCounts.dispatched, statusCounts.delivered, statusCounts.cancelled],
                    backgroundColor: ['#f39c12', '#3498db', '#2ecc71', '#e74c3c'],
                    borderColor: '#fff',
                    borderWidth: 2
                }]
            },
            options: { responsive: true, maintainAspectRatio: true }
        });
    }
}

function logout() {
    localStorage.removeItem('hub_access_token');
    localStorage.removeItem('hub_refresh_token');
    window.location.href = 'loginregister.html';
}

// ============== Initialization ==============
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin Dashboard DOMContentLoaded');
    
    // Load saved settings from localStorage
    const savedCommission = localStorage.getItem('platform_commission_rate') || '10';
    const savedRiderFee = localStorage.getItem('platform_rider_fee') || '5';
    
    if (document.getElementById('defaultCommission')) {
        document.getElementById('defaultCommission').value = savedCommission;
    }
    if (document.getElementById('riderServiceFee')) {
        document.getElementById('riderServiceFee').value = savedRiderFee;
    }
    
    // Make sure dashboard section is visible initially
    const dashboardSection = document.getElementById('dashboardSection');
    if (dashboardSection) {
        dashboardSection.classList.add('active');
        dashboardSection.style.display = 'block';
    }
    
    // Hide all other sections
    ['sellersSection', 'ridersSection', 'reportsSection', 'settingsSection'].forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            section.classList.remove('active');
            section.style.display = 'none';
        }
    });
    
    // Load initial dashboard data
    loadDashboardData();
    
    // Test navigation
    console.log('Testing switchSection function:', typeof switchSection);
    
    console.log('Admin Dashboard Initialized');
});

// ============================================================================
// SELLER MANAGEMENT WITH APPROVAL SYSTEM
// ============================================================================

// Display seller review modal
function displaySellerReviewModal(seller, auditLog) {
    const modal = document.getElementById('sellerReviewModal');
    const modalBody = document.getElementById('sellerReviewModalBody');
    
    // Set currentSellerId for action buttons
    currentSellerId = seller.id || seller.seller_id;
    
    const location = [seller.city, seller.province, seller.region].filter(Boolean).join(', ') || 'Not specified';
    const ownerName = [seller.first_name, seller.last_name].filter(Boolean).join(' ') || 'N/A';
    const appliedDate = new Date(seller.created_at).toLocaleString('en-US', { 
        year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    
    // Status badge styling
    const statusColors = {
        'pending': { bg: '#fff3cd', text: '#856404', border: '#ffc107' },
        'active': { bg: '#d4edda', text: '#155724', border: '#28a745' },
        'declined': { bg: '#f8d7da', text: '#721c24', border: '#dc3545' },
        'suspended': { bg: '#e2e3e5', text: '#383d41', border: '#6c757d' },
        'warning': { bg: '#fff3cd', text: '#856404', border: '#ffc107' },
        'banned': { bg: '#f8d7da', text: '#721c24', border: '#dc3545' }
    };
    const statusColor = statusColors[seller.shop_status || seller.status] || statusColors.pending;
    
    let reviewedInfo = null;
    if (seller.reviewed_at || seller.approved_at) {
        const reviewedDate = new Date(seller.reviewed_at || seller.approved_at).toLocaleString('en-US', { 
            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        const reviewedBy = [seller.reviewed_by_first_name, seller.reviewed_by_last_name].filter(Boolean).join(' ') || 'Admin';
        reviewedInfo = {
            adminName: reviewedBy,
            date: reviewedDate
        };
    }
    
    let rejectionInfo = '';
    if ((seller.status === 'declined' || seller.shop_status === 'suspended') && seller.rejection_reason) {
        rejectionInfo = `
            <div style="grid-column: 1 / -1; background: linear-gradient(135deg, #ffebee, #fff5f5); padding: 20px; border-radius: 8px; margin-top: 10px; border-left: 4px solid #e74c3c;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <i class="fas fa-exclamation-triangle" style="color: #e74c3c; font-size: 20px;"></i>
                    <strong style="color: #c0392b; font-size: 16px;">Rejection/Suspension Reason</strong>
                </div>
                <p style="margin: 0; padding-left: 30px; color: #555; line-height: 1.6;">${seller.rejection_reason}</p>
            </div>
        `;
    }
    
    let auditLogHtml = '';
    if (auditLog && auditLog.length > 0) {
        auditLogHtml = `
            <div style="grid-column: 1 / -1; margin-top: 20px; padding-top: 20px; border-top: 2px solid #e0e0e0;">
                <h3 style="margin-bottom: 15px; display: flex; align-items: center; gap: 10px; color: #2c3e50;">
                    <i class="fas fa-history" style="color: #3498db;"></i> Activity History
                </h3>
                <div style="max-height: 250px; overflow-y: auto; border: 2px solid #ecf0f1; border-radius: 8px; background: #fafafa;">
                    ${auditLog.map((log, index) => {
                        const logDate = new Date(log.created_at).toLocaleString('en-US', { 
                            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        });
                        const adminName = [log.admin_first_name, log.admin_last_name].filter(Boolean).join(' ') || 'System Admin';
                        const actionIcons = {
                            'APPROVED': '✅',
                            'DECLINED': '❌',
                            'WARNING': '⚠️',
                            'SUSPENSION': '⏸️',
                            'FINE': '💰',
                            'RESTRICTION': '🚫',
                            'BAN': '🔨'
                        };
                        const icon = actionIcons[log.action] || '📝';
                        return `
                            <div style="padding: 15px; ${index < auditLog.length - 1 ? 'border-bottom: 1px solid #e0e0e0;' : ''} background: ${index % 2 === 0 ? 'white' : '#f9f9f9'};">
                                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 5px;">
                                    <strong style="color: #2c3e50; display: flex; align-items: center; gap: 8px;">
                                        <span style="font-size: 18px;">${icon}</span>
                                        <span>${log.action}</span>
                                    </strong>
                                    <span style="color: #95a5a6; font-size: 13px;">
                                        <i class="far fa-clock"></i> ${logDate}
                                    </span>
                                </div>
                                <div style="color: #7f8c8d; font-size: 13px; margin-left: 26px;">
                                    <i class="fas fa-user"></i> ${adminName}
                                </div>
                                ${log.reason ? `<div style="margin-top: 8px; margin-left: 26px; padding: 8px; background: #ecf0f1; border-radius: 4px; font-size: 13px; color: #555;"><em>${log.reason}</em></div>` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }
    
    modalBody.innerHTML = `
        <!-- Page Title -->
        <div style="text-align: center; margin-bottom: 35px; padding-bottom: 20px; border-bottom: 3px solid #e0e0e0;">
            <h2 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                <i class="fas fa-file-invoice" style="color: #667eea; margin-right: 10px;"></i>
                Seller Application Review
            </h2>
            <div style="margin-top: 12px;">
                <span style="display: inline-block; padding: 8px 20px; background: ${statusColor.bg}; color: ${statusColor.text}; border: 2px solid ${statusColor.border}; border-radius: 20px; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">
                    ${(seller.shop_status || seller.status || 'Unknown').toUpperCase()}
                </span>
            </div>
        </div>

        <!-- Two-Column Grid: Business & Owner Information -->
        <div style="display: grid; grid-template-columns: 480px 480px; gap: 30px; margin-bottom: 35px; justify-content: center;">
            <!-- Column 1: Business Information -->
            <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 3px solid #667eea;">
                    <div style="background: linear-gradient(135deg, #667eea, #764ba2); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);">
                        <i class="fas fa-store" style="color: white; font-size: 20px;"></i>
                    </div>
                    <h3 style="margin: 0; color: #2d3748; font-size: 20px; font-weight: 700;">Business Information</h3>
                </div>
                
                <div style="display: grid; gap: 20px;">
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-briefcase" style="color: #667eea;"></i> Shop Name
                        </div>
                        <div style="color: #1a202c; font-size: 17px; font-weight: 600; padding-left: 24px;">${seller.business_name || 'N/A'}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-tags" style="color: #667eea;"></i> Category
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${capitalizeText(seller.category || 'N/A')}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-info-circle" style="color: #667eea;"></i> Status
                        </div>
                        <div style="padding-left: 24px;">
                            <span style="display: inline-block; padding: 6px 14px; background: ${statusColor.bg}; color: ${statusColor.text}; border: 1px solid ${statusColor.border}; border-radius: 6px; font-weight: 600; font-size: 14px;">
                                ${capitalizeText(seller.shop_status || seller.status || 'Unknown')}
                            </span>
                        </div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-calendar-plus" style="color: #667eea;"></i> Join Date
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${appliedDate}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-map-marker-alt" style="color: #667eea;"></i> Location
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${location}</div>
                    </div>
                </div>
            </div>
            
            <!-- Column 2: Owner Information -->
            <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 3px solid #764ba2;">
                    <div style="background: linear-gradient(135deg, #764ba2, #667eea); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(118, 75, 162, 0.4);">
                        <i class="fas fa-user-circle" style="color: white; font-size: 20px;"></i>
                    </div>
                    <h3 style="margin: 0; color: #2d3748; font-size: 20px; font-weight: 700;">Owner Information</h3>
                </div>
                
                <div style="display: grid; gap: 20px;">
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-user" style="color: #764ba2;"></i> Owner Name
                        </div>
                        <div style="color: #1a202c; font-size: 17px; font-weight: 600; padding-left: 24px;">${ownerName}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-envelope" style="color: #764ba2;"></i> Email
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${seller.email}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-phone" style="color: #764ba2;"></i> Contact Number
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${seller.contact_number || 'Not provided'}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-map-marked-alt" style="color: #764ba2;"></i> Address
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${location}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-shield-alt" style="color: #764ba2;"></i> Email Verified
                        </div>
                        <div style="padding-left: 24px;">
                            ${seller.is_verified ? 
                                '<span style="display: inline-flex; align-items: center; gap: 6px; background: #d4edda; color: #155724; padding: 6px 14px; border-radius: 6px; font-size: 14px; font-weight: 600;"><i class="fas fa-check-circle"></i> Verified</span>' : 
                                '<span style="display: inline-flex; align-items: center; gap: 6px; background: #f8d7da; color: #721c24; padding: 6px 14px; border-radius: 6px; font-size: 14px; font-weight: 600;"><i class="fas fa-times-circle"></i> Not Verified</span>'
                            }
                        </div>
                    </div>
                    
                    ${reviewedInfo ? `
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-user-check" style="color: #764ba2;"></i> Reviewed By
                        </div>
                        <div style="color: #1a202c; font-size: 15px; padding-left: 24px;">${reviewedInfo.adminName}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-calendar-check" style="color: #764ba2;"></i> Reviewed At
                        </div>
                        <div style="color: #1a202c; font-size: 15px; padding-left: 24px;">${reviewedInfo.date}</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        </div>

        ${rejectionInfo}
        
        <!-- Action Buttons Section -->
        <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <h3 style="margin: 0 0 20px 0; color: #2d3748; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-tools" style="color: #667eea;"></i> Admin Actions
            </h3>
            ${(seller.shop_status === 'pending' || seller.status === 'pending') ? `
                <!-- Pending Seller Actions -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <button onclick="approveSellerApplication()" 
                            style="background: linear-gradient(135deg, #27ae60, #229954); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(39, 174, 96, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(39, 174, 96, 0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(39, 174, 96, 0.3)';"
                            title="Approve this seller application">
                        <i class="fas fa-check-circle"></i> Approve Seller
                    </button>
                    
                    <button onclick="declineSeller()" 
                            style="background: linear-gradient(135deg, #e74c3c, #c0392b); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(231, 76, 60, 0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(231, 76, 60, 0.3)';"
                            title="Decline this seller application">
                        <i class="fas fa-times-circle"></i> Decline Seller
                    </button>
                    
                    <button onclick="requestSellerDocuments()" 
                            style="background: linear-gradient(135deg, #3498db, #2980b9); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(52, 152, 219, 0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(52, 152, 219, 0.3)';"
                            title="Request additional documents from seller">
                        <i class="fas fa-file-upload"></i> Request Documents
                    </button>
                </div>
            ` : (seller.shop_status === 'declined' || seller.status === 'declined') ? `
                <!-- Declined Status - No Actions -->
                <div style="text-align: center; padding: 30px; background: #f8d7da; border-radius: 8px; border: 2px solid #dc3545;">
                    <i class="fas fa-ban" style="font-size: 48px; color: #721c24; margin-bottom: 15px;"></i>
                    <h4 style="margin: 0 0 10px 0; color: #721c24;">Status: Declined</h4>
                    <p style="margin: 0; color: #721c24;">This seller application has been declined. No admin actions available.</p>
                </div>
            ` : `
                <!-- Active Seller Admin Actions -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;">
                    <button onclick="showSellerWarningForm()" 
                            style="background: linear-gradient(135deg, #ffc107, #ffb300); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 193, 7, 0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 193, 7, 0.3)';"
                            title="Issue a warning to the seller">
                        <i class="fas fa-exclamation-triangle"></i> Warning
                    </button>
                    
                    <button onclick="showSellerSuspensionForm()" 
                            style="background: linear-gradient(135deg, #ff9800, #f57c00); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 152, 0, 0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 152, 0, 0.3)';"
                            title="Temporarily suspend the seller's account">
                        <i class="fas fa-pause-circle"></i> Suspension
                    </button>
                    
                    <button onclick="showSellerBanForm()" 
                            style="background: linear-gradient(135deg, #dc3545, #c82333); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(220, 53, 69, 0.4)';"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(220, 53, 69, 0.3)';"
                            title="Permanently ban the seller from the platform">
                        <i class="fas fa-gavel"></i> Permanent Ban
                    </button>
                </div>
            `}
        </div>
        
        ${auditLogHtml}
        
        <!-- Action Form Container -->
        <div id="sellerActionForm" style="display: none; margin-top: 20px;"></div>
    `;
    
    // Action buttons are now dynamically rendered within the modal content
    // No need to show/hide separate action buttons
    
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// Close seller review modal
window.closeSellerReviewModal = function() {
    document.getElementById('sellerReviewModal').style.display = 'none';
    document.body.style.overflow = '';
    selectedSellerForReview = null;
    currentSellerId = null;
    
    // Hide action form if open
    const actionForm = document.getElementById('sellerActionForm');
    if (actionForm) {
        actionForm.style.display = 'none';
        actionForm.innerHTML = '';
    }
};

// Approve seller application
window.approveSellerApplication = async function() {
    if (!currentSellerId) {
        notify.error('No seller selected');
        return;
    }
    
    if (!confirm(`Are you sure you want to APPROVE this seller application?\n\nThis will activate their seller account and allow them to start selling on the platform.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/sellers/${currentSellerId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`
            }
        });
        
        const data = await response.json();
        if (data.success) {
            notify.success('Seller approved successfully!');
            closeSellerReviewModal();
            loadSellersData();
        } else {
            notify.error(data.message || 'Failed to approve seller');
        }
    } catch (error) {
        console.error('Approve seller error:', error);
        notify.error('An error occurred while approving seller');
    }
};

// Show decline reason modal
window.showDeclineReason = function() {
    document.getElementById('declineReasonModal').style.display = 'block';
    document.getElementById('declineReasonText').value = '';
};

// Close decline reason modal
window.closeDeclineReasonModal = function() {
    document.getElementById('declineReasonModal').style.display = 'none';
};

// Confirm decline seller application
window.confirmDeclineSellerApplication = async function() {
    if (!selectedSellerForReview) {
        alert('No seller selected');
        return;
    }
    
    const reason = document.getElementById('declineReasonText').value.trim();
    if (!reason) {
        alert('Please provide a reason for declining');
        return;
    }
    
    try {
        const response = await authFetch(`/api/admin/sellers/${selectedSellerForReview.id}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status: 'declined', reason: reason })
        });
        
        if (!response.ok) throw new Error('Failed to decline seller');
        
        const data = await response.json();
        if (data.success) {
            alert(`❌ Seller "${selectedSellerForReview.business_name}" has been declined.`);
            closeDeclineReasonModal();
            closeSellerReviewModal();
            loadSellersData(); // Reload sellers list
        } else {
            throw new Error(data.message || 'Decline failed');
        }
    } catch (err) {
        console.error('Decline seller error:', err);
        alert('Failed to decline seller: ' + err.message);
    }
};

// ============== Notification System ==============
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 10000;
        font-size: 14px;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Add animation styles
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// Update pending badges when dashboard loads
async function updatePendingBadges() {
    try {
        const response = await authFetch('/api/admin/dashboard');
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.dashboard) {
                // Update sellers badge
                const sellersBadge = document.getElementById('pendingSellersBadge');
                if (sellersBadge && data.dashboard.pending_sellers > 0) {
                    sellersBadge.textContent = data.dashboard.pending_sellers;
                    sellersBadge.style.display = 'inline-block';
                }
                
                // Update riders badge
                const ridersBadge = document.getElementById('pendingRidersBadge');
                if (ridersBadge && data.dashboard.pending_riders > 0) {
                    ridersBadge.textContent = data.dashboard.pending_riders;
                    ridersBadge.style.display = 'inline-block';
                }
            }
        }
    } catch (err) {
        console.error('Error updating badges:', err);
    }
}

// Call on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updatePendingBadges);
} else {
    updatePendingBadges();
}

// ==========================================
// SELLER ACTION PANEL FUNCTIONS
// ==========================================

let currentSellerId = null;
let currentRiderId = null;

function openSellerActionPanel(sellerId) {
    currentSellerId = sellerId;
    const seller = sellers.find(s => s.id === sellerId);
    if (!seller) return;
    
    // Build documents section
    const documents = [];
    if (seller.business_permit) documents.push({ label: 'Business Permit', path: seller.business_permit });
    if (seller.valid_id) documents.push({ label: 'Valid ID', path: seller.valid_id });
    if (seller.address_proof) documents.push({ label: 'Address Proof', path: seller.address_proof });
    if (seller.business_logo) documents.push({ label: 'Business Logo', path: seller.business_logo });
    
    const documentsHTML = documents.length > 0 ? `
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h4 style="margin: 0 0 15px 0; color: #495057; font-size: 14px;">
                <i class="fas fa-folder-open"></i> Uploaded Documents
            </h4>
            <div style="display: grid; gap: 10px;">
                ${documents.map(doc => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; border-radius: 6px; border: 1px solid #dee2e6;">
                        <span style="font-size: 13px; color: #495057;">
                            <i class="fas fa-file-alt" style="color: #667eea; margin-right: 8px;"></i>
                            ${doc.label}
                        </span>
                        <a href="/uploads/${doc.path}" target="_blank" class="btn btn-sm" style="background: #667eea; color: white; padding: 5px 15px; text-decoration: none; border-radius: 4px; font-size: 12px;">
                            <i class="fas fa-eye"></i> View
                        </a>
                    </div>
                `).join('')}
            </div>
        </div>
    ` : `
        <div style="margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 8px; border: 1px solid #ffc107;">
            <p style="margin: 0; color: #856404; font-size: 13px;">
                <i class="fas fa-exclamation-triangle"></i> No documents uploaded yet
            </p>
        </div>
    `;
    
    const infoDiv = document.getElementById('sellerActionInfo');
    infoDiv.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin: 0 0 5px 0;">${seller.businessName || seller.business_name}</h3>
                <p style="margin: 0; color: #666;">Owner: ${seller.firstName || seller.first_name} ${seller.lastName || seller.last_name} (${seller.email})</p>
                <p style="margin: 5px 0 0 0;">
                    <span class="status-badge status-${seller.status || seller.shop_status}">${capitalizeText(seller.status || seller.shop_status)}</span>
                </p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0; color: #666; font-size: 12px;">Seller ID: #${seller.id}</p>
                <p style="margin: 5px 0 0 0; color: #666; font-size: 12px;">Joined: ${formatDate(seller.joinDate || seller.created_at)}</p>
            </div>
        </div>
        ${documentsHTML}
    `;
    
    document.getElementById('sellerActionForm').style.display = 'none';
    document.getElementById('sellerActionForm').innerHTML = '';
    document.getElementById('sellerActionPanel').style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeSellerActionPanel() {
    document.getElementById('sellerActionPanel').style.display = 'none';
    document.body.style.overflow = '';
    currentSellerId = null;
}

function showSellerWarningForm() {
    // Hide the action panel buttons
    const actionPanel = document.querySelector('#sellerActionPanel .action-panel-grid');
    if (actionPanel) {
        actionPanel.style.display = 'none';
    }
    
    const formDiv = document.getElementById('sellerActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container" style="background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: #ff9800; margin: 0; font-size: 20px; font-weight: 600;">
                    <i class="fas fa-exclamation-triangle"></i> Issue Warning
                </h3>
                <button onclick="hideActionForm()" style="background: none; border: none; font-size: 24px; color: #999; cursor: pointer; padding: 0; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;">&times;</button>
            </div>
            <div class="form-group" style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Warning Type *</label>
                <select id="warningType" class="form-control" style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px;">
                    <option value="policy_violation">Policy Violation</option>
                    <option value="product_quality">Product Quality Issue</option>
                    <option value="customer_complaint">Customer Complaint</option>
                    <option value="late_delivery">Late Delivery</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div class="form-group" style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Warning Message *</label>
                <textarea id="warningMessage" placeholder="Enter detailed warning message..." required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px; font-family: inherit; resize: vertical; min-height: 120px;"></textarea>
            </div>
            <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 25px;">
                <button class="btn btn-secondary" onclick="hideActionForm()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">Cancel</button>
                <button class="btn" onclick="submitSellerWarning()" style="padding: 10px 20px; background: #ff9800; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600;">Issue Warning</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    formDiv.style.width = '100%';
    formDiv.style.clear = 'both';
    formDiv.style.marginTop = '20px';
}

function showSellerSuspensionForm() {
    const formDiv = document.getElementById('sellerActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container">
            <h3 style="color: #ff5722; margin-bottom: 15px;">
                <i class="fas fa-pause-circle"></i> Suspend Account
            </h3>
            <div class="form-group">
                <label>Suspension Duration</label>
                <select id="suspensionDuration" class="form-control">
                    <option value="1">1 Day</option>
                    <option value="3">3 Days</option>
                    <option value="7">7 Days</option>
                    <option value="14">14 Days</option>
                    <option value="30">30 Days</option>
                    <option value="custom">Custom</option>
                </select>
            </div>
            <div class="form-group" id="customDurationGroup" style="display: none;">
                <label>Custom Days</label>
                <input type="number" id="customDuration" min="1" placeholder="Enter number of days">
            </div>
            <div class="form-group">
                <label>Suspension Reason *</label>
                <textarea id="suspensionReason" placeholder="Enter reason for suspension..." required></textarea>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideActionForm()">Cancel</button>
                <button class="btn btn-danger" onclick="submitSellerSuspension()">Suspend Seller</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    
    document.getElementById('suspensionDuration').addEventListener('change', (e) => {
        document.getElementById('customDurationGroup').style.display = e.target.value === 'custom' ? 'block' : 'none';
    });
}

function showSellerBanForm() {
    const formDiv = document.getElementById('sellerActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container" style="border: 2px solid #f44336;">
            <h3 style="color: #f44336; margin-bottom: 15px;">
                <i class="fas fa-times-circle"></i> Permanent Ban
            </h3>
            <div style="background: #ffebee; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                <p style="margin: 0; color: #c62828; font-weight: 600;">
                    ⚠️ WARNING: This action is permanent and cannot be undone!
                </p>
                <p style="margin: 10px 0 0 0; color: #c62828;">
                    The seller will be immediately blocked from accessing the platform and all their products will be delisted.
                </p>
            </div>
            <div class="form-group">
                <label>Ban Reason *</label>
                <textarea id="banReason" placeholder="Enter detailed reason for permanent ban..." required></textarea>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 10px;">
                    <input type="checkbox" id="confirmBan" style="width: auto;">
                    <span>I understand this action is permanent and irreversible</span>
                </label>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideActionForm()">Cancel</button>
                <button class="btn btn-danger" onclick="submitSellerBan()">Permanently Ban Seller</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    formDiv.style.width = '100%';
    formDiv.style.clear = 'both';
    formDiv.style.marginTop = '20px';
}

function viewSellerAuditLog() {
    const formDiv = document.getElementById('sellerActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container">
            <h3 style="color: #2196f3; margin-bottom: 15px;">
                <i class="fas fa-history"></i> Audit Log
            </h3>
            <div id="auditLogContent" style="max-height: 400px; overflow-y: auto;">
                <p style="text-align: center; color: #999; padding: 40px;">
                    <i class="fas fa-spinner fa-spin" style="font-size: 24px;"></i><br><br>
                    Loading audit log...
                </p>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideActionForm()">Close</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    
    // Load audit log
    loadSellerAuditLog(currentSellerId);
}

// Submit functions
// ==========================================
// CUSTOM CONFIRMATION MODALS
// ==========================================

function showSellerWarningConfirmationModal(callback) {
    const modal = document.createElement('div');
    modal.id = 'sellerWarningConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 520px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: linear-gradient(to bottom, #ffffff, #fafafa); display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px 32px 24px 32px; text-align: center; background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); border-bottom: 1px solid rgba(250, 204, 21, 0.2); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #FACC15, #EAB308); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; box-shadow: 0 8px 20px rgba(250, 204, 21, 0.3);">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">⚠️</span>
                </div>
                <h2 style="margin: 0; color: #92400E; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">Issue Warning</h2>
            </div>
            <div style="padding: 32px; background: white; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #FACC15 #FEF3C7;">
                <style>
                    #sellerWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #sellerWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FEF3C7;
                        border-radius: 4px;
                    }
                    #sellerWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #FACC15;
                        border-radius: 4px;
                    }
                    #sellerWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #EAB308;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 24px 0; text-align: left;">
                    You are about to issue a formal warning to this <strong style="color: #1F2937; font-weight: 600;">seller</strong>.
                </p>
                <div style="background: #FEF3C7; border-left: 4px solid #FACC15; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #78350F; line-height: 1.6; margin: 0 0 8px 0;">
                        <strong>What this means:</strong>
                    </p>
                    <ul style="font-size: 14px; color: #92400E; line-height: 1.7; margin: 0; padding-left: 20px;">
                        <li>A warning serves as an official notice for violating platform policies</li>
                        <li>This will be recorded in their account history</li>
                        <li><strong>Account access will NOT be restricted</strong></li>
                    </ul>
                </div>
                <p style="font-size: 15px; color: #1F2937; line-height: 1.7; margin: 0 0 28px 0; text-align: center; font-weight: 600;">
                    Do you want to proceed with issuing this warning?
                </p>
                <div style="display: flex; gap: 10px; justify-content: flex-end; padding-top: 24px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelSellerWarning" style="padding: 11px 22px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmSellerWarning" style="padding: 11px 22px; background: linear-gradient(135deg, #FACC15, #EAB308); color: #78350F; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; box-shadow: 0 4px 12px rgba(250, 204, 21, 0.35); letter-spacing: 0.2px;" onmouseover="this.style.background='linear-gradient(135deg, #EAB308, #CA8A04)'; this.style.boxShadow='0 6px 16px rgba(250, 204, 21, 0.45)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='linear-gradient(135deg, #FACC15, #EAB308)'; this.style.boxShadow='0 4px 12px rgba(250, 204, 21, 0.35)'; this.style.transform='translateY(0)'">Confirm — Issue Warning</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    document.getElementById('cancelSellerWarning').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    document.getElementById('confirmSellerWarning').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
        if (callback) callback();
    };
}

function showSellerSuspensionConfirmationModal(duration, callback) {
    const modal = document.createElement('div');
    modal.id = 'sellerSuspensionConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 520px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: linear-gradient(to bottom, #ffffff, #fafafa); display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px 32px 24px 32px; text-align: center; background: linear-gradient(135deg, #FED7AA 0%, #FDBA74 100%); border-bottom: 1px solid rgba(251, 146, 60, 0.2); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #FB923C, #F97316); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; box-shadow: 0 8px 20px rgba(251, 146, 60, 0.3);">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">⛔</span>
                </div>
                <h2 style="margin: 0; color: #9A3412; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">Temporary Suspension</h2>
            </div>
            <div style="padding: 32px; background: white; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #FB923C #FED7AA;">
                <style>
                    #sellerSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #sellerSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FED7AA;
                        border-radius: 4px;
                    }
                    #sellerSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #FB923C;
                        border-radius: 4px;
                    }
                    #sellerSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #F97316;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 20px 0; text-align: left;">
                    You are about to temporarily suspend this <strong style="color: #1F2937; font-weight: 600;">seller</strong> for <strong style="color: #FB923C; font-size: 16px; font-weight: 700;">${duration} day(s)</strong>.
                </p>
                <div style="background: #FED7AA; border-left: 4px solid #FB923C; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #7C2D12; line-height: 1.6; margin: 0 0 8px 0; font-weight: 600;">
                        During the suspension period:
                    </p>
                    <ul style="font-size: 14px; color: #9A3412; line-height: 1.7; margin: 0; padding-left: 20px;">
                        <li>They cannot log in to their account</li>
                        <li>They cannot perform any activity</li>
                        <li>Their shop will be disabled</li>
                    </ul>
                </div>
                <p style="font-size: 15px; color: #1F2937; line-height: 1.7; margin: 0 0 28px 0; text-align: center; font-weight: 600;">
                    Do you want to continue with the suspension?
                </p>
                <div style="display: flex; gap: 10px; justify-content: flex-end; padding-top: 24px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelSellerSuspension" style="padding: 11px 22px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmSellerSuspension" style="padding: 11px 22px; background: linear-gradient(135deg, #FB923C, #F97316); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; box-shadow: 0 4px 12px rgba(251, 146, 60, 0.35); letter-spacing: 0.2px;" onmouseover="this.style.background='linear-gradient(135deg, #F97316, #EA580C)'; this.style.boxShadow='0 6px 16px rgba(251, 146, 60, 0.45)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='linear-gradient(135deg, #FB923C, #F97316)'; this.style.boxShadow='0 4px 12px rgba(251, 146, 60, 0.35)'; this.style.transform='translateY(0)'">Confirm — Suspend Account</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    document.getElementById('cancelSellerSuspension').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    document.getElementById('confirmSellerSuspension').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
        if (callback) callback();
    };
}

function showSellerBanConfirmationModal(callback) {
    const modal = document.createElement('div');
    modal.id = 'sellerBanConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 520px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: linear-gradient(to bottom, #ffffff, #fafafa); border: 2px solid #DC2626; display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px 32px 24px 32px; text-align: center; background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%); border-bottom: 1px solid rgba(220, 38, 38, 0.2); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #DC2626, #991B1B); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; box-shadow: 0 8px 20px rgba(220, 38, 38, 0.4);">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">🔥</span>
                </div>
                <h2 style="margin: 0; color: #991B1B; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">Permanent Ban</h2>
            </div>
            <div style="padding: 32px; background: white; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #DC2626 #FEE2E2;">
                <style>
                    #sellerBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #sellerBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FEE2E2;
                        border-radius: 4px;
                    }
                    #sellerBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #DC2626;
                        border-radius: 4px;
                    }
                    #sellerBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #991B1B;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 20px 0; text-align: left;">
                    You are about to permanently ban this <strong style="color: #1F2937; font-weight: 600;">seller</strong>.
                </p>
                <div style="background: #FEE2E2; border-left: 4px solid #DC2626; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #7F1D1D; line-height: 1.6; margin: 0 0 8px 0; font-weight: 600;">
                        This action will:
                    </p>
                    <ul style="font-size: 14px; color: #991B1B; line-height: 1.7; margin: 0; padding-left: 20px;">
                        <li>Permanently deactivate the account</li>
                        <li>Remove all access to services</li>
                        <li>Completely restrict future login or activity</li>
                        <li><strong style="color: #DC2626;">⚠️ Cannot be undone</strong></li>
                    </ul>
                </div>
                <p style="font-size: 15px; color: #DC2626; line-height: 1.7; margin: 0 0 28px 0; text-align: center; font-weight: 700;">
                    Are you absolutely sure you want to proceed with this irreversible action?
                </p>
                <div style="display: flex; gap: 10px; justify-content: flex-end; padding-top: 24px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelSellerBan" style="padding: 11px 22px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmSellerBan" style="padding: 11px 22px; background: linear-gradient(135deg, #DC2626, #991B1B); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4); letter-spacing: 0.2px;" onmouseover="this.style.background='linear-gradient(135deg, #991B1B, #7F1D1D)'; this.style.boxShadow='0 6px 16px rgba(220, 38, 38, 0.5)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='linear-gradient(135deg, #DC2626, #991B1B)'; this.style.boxShadow='0 4px 12px rgba(220, 38, 38, 0.4)'; this.style.transform='translateY(0)'">Confirm — Permanently Ban</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    document.getElementById('cancelSellerBan').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    document.getElementById('confirmSellerBan').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
        if (callback) callback();
    };
}

// Rider confirmation modals
function showRiderWarningConfirmationModal(callback) {
    const modal = document.createElement('div');
    modal.id = 'riderWarningConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 520px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: linear-gradient(to bottom, #ffffff, #fafafa); display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px 32px 24px 32px; text-align: center; background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); border-bottom: 1px solid rgba(250, 204, 21, 0.2); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #FACC15, #EAB308); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; box-shadow: 0 8px 20px rgba(250, 204, 21, 0.3);">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">⚠️</span>
                </div>
                <h2 style="margin: 0; color: #92400E; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">Issue Warning</h2>
            </div>
            <div style="padding: 32px; background: white; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #FACC15 #FEF3C7;">
                <style>
                    #riderWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #riderWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FEF3C7;
                        border-radius: 4px;
                    }
                    #riderWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #FACC15;
                        border-radius: 4px;
                    }
                    #riderWarningConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #EAB308;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 24px 0; text-align: left;">
                    You are about to issue a formal warning to this <strong style="color: #1F2937; font-weight: 600;">rider</strong>.
                </p>
                <div style="background: #FEF3C7; border-left: 4px solid #FACC15; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #78350F; line-height: 1.6; margin: 0 0 8px 0;">
                        <strong>What this means:</strong>
                    </p>
                    <ul style="font-size: 14px; color: #92400E; line-height: 1.7; margin: 0; padding-left: 20px;">
                        <li>A warning serves as an official notice for violating platform policies</li>
                        <li>This will be recorded in their account history</li>
                        <li><strong>Account access will NOT be restricted</strong></li>
                    </ul>
                </div>
                <p style="font-size: 15px; color: #1F2937; line-height: 1.7; margin: 0 0 28px 0; text-align: center; font-weight: 600;">
                    Do you want to proceed with issuing this warning?
                </p>
                <div style="display: flex; gap: 10px; justify-content: flex-end; padding-top: 24px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelRiderWarning" style="padding: 11px 22px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmRiderWarning" style="padding: 11px 22px; background: linear-gradient(135deg, #FACC15, #EAB308); color: #78350F; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; box-shadow: 0 4px 12px rgba(250, 204, 21, 0.35); letter-spacing: 0.2px;" onmouseover="this.style.background='linear-gradient(135deg, #EAB308, #CA8A04)'; this.style.boxShadow='0 6px 16px rgba(250, 204, 21, 0.45)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='linear-gradient(135deg, #FACC15, #EAB308)'; this.style.boxShadow='0 4px 12px rgba(250, 204, 21, 0.35)'; this.style.transform='translateY(0)'">Confirm — Issue Warning</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    document.getElementById('cancelRiderWarning').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    document.getElementById('confirmRiderWarning').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
        if (callback) callback();
    };
}

function showRiderSuspensionConfirmationModal(duration, callback) {
    const modal = document.createElement('div');
    modal.id = 'riderSuspensionConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 520px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: linear-gradient(to bottom, #ffffff, #fafafa); display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px 32px 24px 32px; text-align: center; background: linear-gradient(135deg, #FED7AA 0%, #FDBA74 100%); border-bottom: 1px solid rgba(251, 146, 60, 0.2); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #FB923C, #F97316); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; box-shadow: 0 8px 20px rgba(251, 146, 60, 0.3);">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">⛔</span>
                </div>
                <h2 style="margin: 0; color: #9A3412; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">Temporary Suspension</h2>
            </div>
            <div style="padding: 32px; background: white; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #FB923C #FED7AA;">
                <style>
                    #riderSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #riderSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FED7AA;
                        border-radius: 4px;
                    }
                    #riderSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #FB923C;
                        border-radius: 4px;
                    }
                    #riderSuspensionConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #F97316;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 20px 0; text-align: left;">
                    You are about to temporarily suspend this <strong style="color: #1F2937; font-weight: 600;">rider</strong> for <strong style="color: #FB923C; font-size: 16px; font-weight: 700;">${duration} day(s)</strong>.
                </p>
                <div style="background: #FED7AA; border-left: 4px solid #FB923C; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #7C2D12; line-height: 1.6; margin: 0 0 8px 0; font-weight: 600;">
                        During the suspension period:
                    </p>
                    <ul style="font-size: 14px; color: #9A3412; line-height: 1.7; margin: 0; padding-left: 20px;">
                        <li>They cannot log in to their account</li>
                        <li>They cannot perform any activity</li>
                        <li>Their rider services will be disabled</li>
                    </ul>
                </div>
                <p style="font-size: 15px; color: #1F2937; line-height: 1.7; margin: 0 0 28px 0; text-align: center; font-weight: 600;">
                    Do you want to continue with the suspension?
                </p>
                <div style="display: flex; gap: 10px; justify-content: flex-end; padding-top: 24px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelRiderSuspension" style="padding: 11px 22px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmRiderSuspension" style="padding: 11px 22px; background: linear-gradient(135deg, #FB923C, #F97316); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; box-shadow: 0 4px 12px rgba(251, 146, 60, 0.35); letter-spacing: 0.2px;" onmouseover="this.style.background='linear-gradient(135deg, #F97316, #EA580C)'; this.style.boxShadow='0 6px 16px rgba(251, 146, 60, 0.45)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='linear-gradient(135deg, #FB923C, #F97316)'; this.style.boxShadow='0 4px 12px rgba(251, 146, 60, 0.35)'; this.style.transform='translateY(0)'">Confirm — Suspend Account</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    document.getElementById('cancelRiderSuspension').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    document.getElementById('confirmRiderSuspension').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
        if (callback) callback();
    };
}

function showRiderBanConfirmationModal(callback) {
    const modal = document.createElement('div');
    modal.id = 'riderBanConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 520px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: linear-gradient(to bottom, #ffffff, #fafafa); border: 2px solid #DC2626; display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px 32px 24px 32px; text-align: center; background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%); border-bottom: 1px solid rgba(220, 38, 38, 0.2); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #DC2626, #991B1B); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; box-shadow: 0 8px 20px rgba(220, 38, 38, 0.4);">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">🔥</span>
                </div>
                <h2 style="margin: 0; color: #991B1B; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">Permanent Ban</h2>
            </div>
            <div style="padding: 32px; background: white; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #DC2626 #FEE2E2;">
                <style>
                    #riderBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #riderBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FEE2E2;
                        border-radius: 4px;
                    }
                    #riderBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #DC2626;
                        border-radius: 4px;
                    }
                    #riderBanConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #991B1B;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 20px 0; text-align: left;">
                    You are about to permanently ban this <strong style="color: #1F2937; font-weight: 600;">rider</strong>.
                </p>
                <div style="background: #FEE2E2; border-left: 4px solid #DC2626; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #7F1D1D; line-height: 1.6; margin: 0 0 8px 0; font-weight: 600;">
                        This action will:
                    </p>
                    <ul style="font-size: 14px; color: #991B1B; line-height: 1.7; margin: 0; padding-left: 20px;">
                        <li>Permanently deactivate the account</li>
                        <li>Remove all access to services</li>
                        <li>Completely restrict future login or activity</li>
                        <li><strong style="color: #DC2626;">⚠️ Cannot be undone</strong></li>
                    </ul>
                </div>
                <p style="font-size: 15px; color: #DC2626; line-height: 1.7; margin: 0 0 28px 0; text-align: center; font-weight: 700;">
                    Are you absolutely sure you want to proceed with this irreversible action?
                </p>
                <div style="display: flex; gap: 10px; justify-content: flex-end; padding-top: 24px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelRiderBan" style="padding: 11px 22px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmRiderBan" style="padding: 11px 22px; background: linear-gradient(135deg, #DC2626, #991B1B); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4); letter-spacing: 0.2px;" onmouseover="this.style.background='linear-gradient(135deg, #991B1B, #7F1D1D)'; this.style.boxShadow='0 6px 16px rgba(220, 38, 38, 0.5)'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='linear-gradient(135deg, #DC2626, #991B1B)'; this.style.boxShadow='0 4px 12px rgba(220, 38, 38, 0.4)'; this.style.transform='translateY(0)'">Confirm — Permanently Ban</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    document.getElementById('cancelRiderBan').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    document.getElementById('confirmRiderBan').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
        if (callback) callback();
    };
}

async function submitSellerWarning() {
    const warningType = document.getElementById('warningType').value;
    const message = document.getElementById('warningMessage').value.trim();
    
    if (!message) {
        showNotification('Please enter a warning message', 'error');
        return;
    }
    
    if (!currentSellerId) {
        showNotification('No seller selected', 'error');
        return;
    }
    
    showSellerWarningConfirmationModal(() => {
        executeSellerWarning(warningType, message);
    });
}

async function executeSellerWarning(warningType, message) {
    try {
        const reason = `${warningType}: ${message}`;
        const response = await authFetch(`/api/admin/sellers/${currentSellerId}/status`, {
            method: 'PUT',
            body: JSON.stringify({
                status: 'warning',
                reason: reason
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('⚠️ Warning issued successfully', 'success');
            // Hide action form and refresh seller data
            const actionForm = document.getElementById('sellerActionForm');
            if (actionForm) {
                actionForm.style.display = 'none';
                actionForm.innerHTML = '';
            }
            // Show the action panel buttons again
            const actionPanel = document.querySelector('#sellerActionPanel .action-panel-grid');
            if (actionPanel) {
                actionPanel.style.display = 'grid';
            }
            // Reload seller details and table with a small delay to ensure DB commit
            if (selectedSellerForReview) {
                setTimeout(() => {
                    viewSellerDetails(selectedSellerForReview.id);
                }, 500);
            }
            setTimeout(() => {
                loadSellersData();
            }, 500);
        } else {
            showNotification(data.message || data.error || 'Failed to issue warning', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('An error occurred while issuing warning', 'error');
    }
}

async function submitSellerSuspension() {
    let duration = document.getElementById('suspensionDuration').value;
    if (duration === 'custom') {
        duration = document.getElementById('customDuration').value;
    }
    const reason = document.getElementById('suspensionReason').value.trim();

    // Validate seller selection
    if (!currentSellerId) {
        showNotification('No seller selected', 'error');
        return;
    }
    // Validate reason
    if (!reason) {
        showNotification('Please enter a suspension reason', 'error');
        return;
    }
    // Validate duration
    const durationInt = parseInt(duration, 10);
    if (isNaN(durationInt) || durationInt <= 0) {
        showNotification('Please specify a valid suspension duration in days', 'error');
        return;
    }
    
    showSellerSuspensionConfirmationModal(duration, () => {
        executeSellerSuspension(durationInt, reason);
    });
}

async function executeSellerSuspension(durationInt, reason) {
    try {
        const response = await authFetch(`/api/admin/sellers/${currentSellerId}/status`, {
            method: 'PUT',
            body: JSON.stringify({
                status: 'suspended',
                reason: reason,
                duration_days: durationInt
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification(`⏸️ Seller suspended successfully for ${durationInt} day(s)`, 'success');
            // Hide action form and refresh seller data
            const actionForm = document.getElementById('sellerActionForm');
            if (actionForm) {
                actionForm.style.display = 'none';
                actionForm.innerHTML = '';
            }
            // Show the action panel buttons again
            const actionPanel = document.querySelector('#sellerActionPanel .action-panel-grid');
            if (actionPanel) {
                actionPanel.style.display = 'grid';
            }
            // Close modal first
            closeSellerActionPanel();
            // Reload seller details and table with a small delay to ensure DB commit
            setTimeout(() => {
                loadSellersData();
            }, 500);
        } else {
            showNotification(data.message || data.error || 'Failed to suspend seller', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('An error occurred while suspending seller', 'error');
    }
}

async function submitSellerBan() {
    const reason = document.getElementById('banReason').value.trim();
    const confirmed = document.getElementById('confirmBan').checked;
    
    // Validate seller selection
    if (!currentSellerId) {
        showNotification('No seller selected', 'error');
        return;
    }
    if (!reason) {
        showNotification('Please enter a reason for the ban', 'error');
        return;
    }
    
    if (!confirmed) {
        showNotification('Please confirm you understand this action is permanent', 'error');
        return;
    }
    
    showSellerBanConfirmationModal(() => {
        executeSellerBan(reason);
    });
}

async function executeSellerBan(reason) {
    try {
        console.log('🔨 Banning seller:', currentSellerId, 'Reason:', reason);
        const response = await authFetch(`/api/admin/sellers/${currentSellerId}/status`, {
            method: 'PUT',
            body: JSON.stringify({
                status: 'banned',
                reason: reason
            })
        });
        
        const data = await response.json();
        console.log('Ban response:', data);
        
        if (data.success) {
            showNotification('🔨 Seller banned permanently', 'success');
            // Hide action form and refresh seller data
            const actionForm = document.getElementById('sellerActionForm');
            if (actionForm) {
                actionForm.style.display = 'none';
                actionForm.innerHTML = '';
            }
            // Show the action panel buttons again
            const actionPanel = document.querySelector('#sellerActionPanel .action-panel-grid');
            if (actionPanel) {
                actionPanel.style.display = 'grid';
            }
            // Close modal first
            closeSellerActionPanel();
            closeSellerReviewModal();
            // Force reload seller details and table with a small delay to ensure DB commit
            setTimeout(() => {
                console.log('🔄 Reloading sellers data after ban...');
                loadSellersData();
                // Also force a page refresh of the sellers table
                const sellersTable = document.getElementById('sellersTableBody');
                if (sellersTable) {
                    sellersTable.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 40px; color: #999;"><p>Reloading...</p></td></tr>';
                }
            }, 500);
        } else {
            console.error('Ban failed:', data);
            showNotification(data.message || data.error || 'Failed to ban seller', 'error');
        }
    } catch (error) {
        console.error('Error banning seller:', error);
        showNotification('An error occurred while banning seller: ' + error.message, 'error');
    }
}

// Show delete rider confirmation modal
function showRiderDeleteConfirmationModal(riderId, riderName, callback) {
    const modal = document.createElement('div');
    modal.id = 'riderDeleteConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 480px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: white; border: 2px solid #DC2626; display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px; text-align: center; background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #DC2626, #991B1B); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; box-shadow: 0 8px 20px rgba(220, 38, 38, 0.4);">
                    <i class="fas fa-trash-alt" style="font-size: 28px; color: white; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));"></i>
                </div>
                <h2 style="margin: 0; color: #991B1B; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">🗑️ Permanently Delete Account</h2>
            </div>
            <div style="padding: 32px; background: white; width: 100%; box-sizing: border-box; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #DC2626 #FEE2E2;">
                <style>
                    #riderDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #riderDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FEE2E2;
                        border-radius: 4px;
                    }
                    #riderDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #DC2626;
                        border-radius: 4px;
                    }
                    #riderDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #991B1B;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 16px 0; text-align: center;">
                    You are about to <strong style="color: #DC2626; font-weight: 700;">PERMANENTLY DELETE</strong> the <strong style="color: #1F2937; font-weight: 600;">rider</strong>
                </p>
                <p style="font-size: 16px; color: #DC2626; line-height: 1.6; margin: 0 0 24px 0; text-align: center; font-weight: 700; padding: 12px 16px; background: #FEE2E2; border-radius: 8px; border: 1px solid #FECACA;">
                    "${riderName}"
                </p>
                <div style="background: #FEE2E2; border-left: 4px solid #DC2626; padding: 18px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #7F1D1D; line-height: 1.6; margin: 0 0 12px 0; font-weight: 600; text-align: center;">
                        This action will:
                    </p>
                    <ul style="font-size: 13px; color: #991B1B; line-height: 1.8; margin: 0; padding-left: 20px; text-align: left; list-style-position: inside;">
                        <li>Completely remove the account from the system</li>
                        <li>Delete ALL associated data, records, and history</li>
                        <li>Disable any future login or recovery</li>
                        <li style="margin-top: 8px;"><strong style="color: #DC2626;">⚠️ This action is PERMANENT and CANNOT be undone</strong></li>
                    </ul>
                </div>
                <div style="margin-bottom: 24px;">
                    <label style="display: block; font-size: 13px; color: #374151; font-weight: 600; margin-bottom: 10px; text-align: center;">
                        To confirm, type <strong style="color: #DC2626; font-size: 14px;">DELETE</strong> below:
                    </label>
                    <input type="text" id="riderDeleteConfirmInput" placeholder="TYPE DELETE TO CONFIRM" 
                           style="width: 100%; padding: 14px 16px; border: 2px solid #D1D5DB; border-radius: 8px; font-size: 15px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; text-align: center; transition: all 0.2s; box-sizing: border-box;"
                           oninput="document.getElementById('confirmRiderDelete').disabled = this.value !== 'DELETE'; if (this.value === 'DELETE') { this.style.borderColor = '#DC2626'; this.style.boxShadow = '0 0 0 3px rgba(220, 38, 38, 0.1)'; this.style.background = '#FEE2E2'; } else { this.style.borderColor = '#D1D5DB'; this.style.boxShadow = 'none'; this.style.background = 'white'; }">
                </div>
                <div style="display: flex; gap: 10px; justify-content: center; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelRiderDelete" style="padding: 12px 24px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmRiderDelete" disabled style="padding: 12px 24px; background: #9CA3AF; color: white; border: none; border-radius: 8px; cursor: not-allowed; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px; opacity: 0.6;" onmouseover="if (!this.disabled) { this.style.background='linear-gradient(135deg, #991B1B, #7F1D1D)'; this.style.boxShadow='0 6px 16px rgba(220, 38, 38, 0.5)'; this.style.transform='translateY(-1px)'; }" onmouseout="if (!this.disabled) { this.style.background='linear-gradient(135deg, #DC2626, #991B1B)'; this.style.boxShadow='0 4px 12px rgba(220, 38, 38, 0.4)'; this.style.transform='translateY(0)'; }">Confirm — Permanently Delete</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    const confirmBtn = document.getElementById('confirmRiderDelete');
    const inputField = document.getElementById('riderDeleteConfirmInput');
    
    // Update button style when enabled
    inputField.addEventListener('input', function() {
        if (this.value === 'DELETE') {
            confirmBtn.disabled = false;
            confirmBtn.style.background = 'linear-gradient(135deg, #DC2626, #991B1B)';
            confirmBtn.style.cursor = 'pointer';
            confirmBtn.style.opacity = '1';
            confirmBtn.style.boxShadow = '0 4px 12px rgba(220, 38, 38, 0.4)';
        } else {
            confirmBtn.disabled = true;
            confirmBtn.style.background = '#9CA3AF';
            confirmBtn.style.cursor = 'not-allowed';
            confirmBtn.style.opacity = '0.6';
            confirmBtn.style.boxShadow = 'none';
        }
    });
    
    // Allow Enter key to submit when DELETE is typed
    inputField.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && this.value === 'DELETE' && !confirmBtn.disabled) {
            confirmBtn.click();
        }
    });
    
    document.getElementById('cancelRiderDelete').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    confirmBtn.onclick = () => {
        if (inputField.value === 'DELETE') {
            modal.remove();
            document.body.style.overflow = '';
            if (callback) callback();
        }
    };
    
    // Focus on input field
    setTimeout(() => inputField.focus(), 100);
    
    // Prevent closing by clicking outside
    modal.onclick = (e) => {
        if (e.target === modal) {
            // Do nothing - prevent closing
        }
    };
}

// Delete rider function
window.deleteRider = async function(riderId, riderName) {
    if (!riderId) {
        showNotification('No rider selected', 'error');
        return;
    }
    
    showRiderDeleteConfirmationModal(riderId, riderName, async () => {
        try {
            console.log('🗑️ Deleting rider:', riderId, riderName);
            const response = await authFetch(`/api/admin/riders/${riderId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            console.log('Delete response:', data);
            
            if (data.success) {
                showNotification(`✅ Rider "${riderName}" deleted successfully`, 'success');
                // Reload riders list
                setTimeout(() => {
                    console.log('🔄 Reloading riders data after deletion...');
                    loadRidersData();
                }, 500);
            } else {
                console.error('Delete failed:', data);
                showNotification(data.message || data.error || 'Failed to delete rider', 'error');
            }
        } catch (error) {
            console.error('Error deleting rider:', error);
            showNotification('An error occurred while deleting rider: ' + error.message, 'error');
        }
    });
};

// Show delete seller confirmation modal
function showSellerDeleteConfirmationModal(sellerId, businessName, callback) {
    const modal = document.createElement('div');
    modal.id = 'sellerDeleteConfirmModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10000';
    modal.style.animation = 'fadeIn 0.3s ease';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
    modal.style.backdropFilter = 'blur(4px)';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 480px; width: 90%; max-height: 90vh; padding: 0; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.1); overflow: hidden; animation: slideDown 0.3s ease; background: white; border: 2px solid #DC2626; display: flex !important; flex-direction: column !important;">
            <div style="padding: 32px; text-align: center; background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%); flex-shrink: 0;">
                <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #DC2626, #991B1B); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; box-shadow: 0 8px 20px rgba(220, 38, 38, 0.4);">
                    <i class="fas fa-trash-alt" style="font-size: 28px; color: white; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));"></i>
                </div>
                <h2 style="margin: 0; color: #991B1B; font-size: 22px; font-weight: 700; letter-spacing: -0.3px; text-shadow: 0 1px 2px rgba(255,255,255,0.8);">🗑️ Permanently Delete Account</h2>
            </div>
            <div style="padding: 32px; background: white; width: 100%; box-sizing: border-box; overflow-y: auto; flex: 1; min-height: 0; scrollbar-width: thin; scrollbar-color: #DC2626 #FEE2E2;">
                <style>
                    #sellerDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar {
                        width: 8px;
                    }
                    #sellerDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar-track {
                        background: #FEE2E2;
                        border-radius: 4px;
                    }
                    #sellerDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb {
                        background: #DC2626;
                        border-radius: 4px;
                    }
                    #sellerDeleteConfirmModal .modal-content > div:last-child::-webkit-scrollbar-thumb:hover {
                        background: #991B1B;
                    }
                </style>
                <p style="font-size: 15px; color: #4B5563; line-height: 1.7; margin: 0 0 16px 0; text-align: center;">
                    You are about to <strong style="color: #DC2626; font-weight: 700;">PERMANENTLY DELETE</strong> the <strong style="color: #1F2937; font-weight: 600;">seller</strong>
                </p>
                <p style="font-size: 16px; color: #DC2626; line-height: 1.6; margin: 0 0 24px 0; text-align: center; font-weight: 700; padding: 12px 16px; background: #FEE2E2; border-radius: 8px; border: 1px solid #FECACA;">
                    "${businessName}"
                </p>
                <div style="background: #FEE2E2; border-left: 4px solid #DC2626; padding: 18px; border-radius: 8px; margin-bottom: 24px;">
                    <p style="font-size: 14px; color: #7F1D1D; line-height: 1.6; margin: 0 0 12px 0; font-weight: 600; text-align: center;">
                        This action will:
                    </p>
                    <ul style="font-size: 13px; color: #991B1B; line-height: 1.8; margin: 0; padding-left: 20px; text-align: left; list-style-position: inside;">
                        <li>Completely remove the account from the system</li>
                        <li>Delete ALL associated data, records, and history</li>
                        <li>Delete all products and reviews</li>
                        <li>Disable any future login or recovery</li>
                        <li style="margin-top: 8px;"><strong style="color: #DC2626;">⚠️ This action is PERMANENT and CANNOT be undone</strong></li>
                    </ul>
                </div>
                <div style="margin-bottom: 24px;">
                    <label style="display: block; font-size: 13px; color: #374151; font-weight: 600; margin-bottom: 10px; text-align: center;">
                        To confirm, type <strong style="color: #DC2626; font-size: 14px;">DELETE</strong> below:
                    </label>
                    <input type="text" id="sellerDeleteConfirmInput" placeholder="TYPE DELETE TO CONFIRM" 
                           style="width: 100%; padding: 14px 16px; border: 2px solid #D1D5DB; border-radius: 8px; font-size: 15px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; text-align: center; transition: all 0.2s; box-sizing: border-box;"
                           oninput="document.getElementById('confirmSellerDelete').disabled = this.value !== 'DELETE'; if (this.value === 'DELETE') { this.style.borderColor = '#DC2626'; this.style.boxShadow = '0 0 0 3px rgba(220, 38, 38, 0.1)'; this.style.background = '#FEE2E2'; } else { this.style.borderColor = '#D1D5DB'; this.style.boxShadow = 'none'; this.style.background = 'white'; }">
                </div>
                <div style="display: flex; gap: 10px; justify-content: center; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                    <button id="cancelSellerDelete" style="padding: 12px 24px; background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px;" onmouseover="this.style.background='#E5E7EB'; this.style.borderColor='#9CA3AF'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#F3F4F6'; this.style.borderColor='#D1D5DB'; this.style.transform='translateY(0)'">Cancel</button>
                    <button id="confirmSellerDelete" disabled style="padding: 12px 24px; background: #9CA3AF; color: white; border: none; border-radius: 8px; cursor: not-allowed; font-size: 14px; font-weight: 600; transition: all 0.2s; letter-spacing: 0.2px; opacity: 0.6;" onmouseover="if (!this.disabled) { this.style.background='linear-gradient(135deg, #991B1B, #7F1D1D)'; this.style.boxShadow='0 6px 16px rgba(220, 38, 38, 0.5)'; this.style.transform='translateY(-1px)'; }" onmouseout="if (!this.disabled) { this.style.background='linear-gradient(135deg, #DC2626, #991B1B)'; this.style.boxShadow='0 4px 12px rgba(220, 38, 38, 0.4)'; this.style.transform='translateY(0)'; }">Confirm — Permanently Delete</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    
    const confirmBtn = document.getElementById('confirmSellerDelete');
    const inputField = document.getElementById('sellerDeleteConfirmInput');
    
    // Update button style when enabled
    inputField.addEventListener('input', function() {
        if (this.value === 'DELETE') {
            confirmBtn.disabled = false;
            confirmBtn.style.background = 'linear-gradient(135deg, #DC2626, #991B1B)';
            confirmBtn.style.cursor = 'pointer';
            confirmBtn.style.opacity = '1';
            confirmBtn.style.boxShadow = '0 4px 12px rgba(220, 38, 38, 0.4)';
        } else {
            confirmBtn.disabled = true;
            confirmBtn.style.background = '#9CA3AF';
            confirmBtn.style.cursor = 'not-allowed';
            confirmBtn.style.opacity = '0.6';
            confirmBtn.style.boxShadow = 'none';
        }
    });
    
    // Allow Enter key to submit when DELETE is typed
    inputField.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && this.value === 'DELETE' && !confirmBtn.disabled) {
            confirmBtn.click();
        }
    });
    
    document.getElementById('cancelSellerDelete').onclick = () => {
        modal.remove();
        document.body.style.overflow = '';
    };
    
    confirmBtn.onclick = () => {
        if (inputField.value === 'DELETE') {
            modal.remove();
            document.body.style.overflow = '';
            if (callback) callback();
        }
    };
    
    // Focus on input field
    setTimeout(() => inputField.focus(), 100);
    
    // Prevent closing by clicking outside
    modal.onclick = (e) => {
        if (e.target === modal) {
            // Do nothing - prevent closing
        }
    };
}

// Delete seller function
window.deleteSeller = async function(sellerId, businessName) {
    if (!sellerId) {
        showNotification('No seller selected', 'error');
        return;
    }
    
    showSellerDeleteConfirmationModal(sellerId, businessName, async () => {
        try {
            console.log('🗑️ Deleting seller:', sellerId, businessName);
            const response = await authFetch(`/api/admin/sellers/${sellerId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            console.log('Delete response:', data);
            
            if (data.success) {
                showNotification(`✅ Seller "${businessName}" deleted successfully`, 'success');
                // Reload sellers list
                setTimeout(() => {
                    console.log('🔄 Reloading sellers data after deletion...');
                    loadSellersData();
                }, 500);
            } else {
                console.error('Delete failed:', data);
                showNotification(data.message || data.error || 'Failed to delete seller', 'error');
            }
        } catch (error) {
            console.error('Error deleting seller:', error);
            showNotification('An error occurred while deleting seller: ' + error.message, 'error');
        }
    });
};

async function loadSellerAuditLog(sellerId) {
    try {
        const response = await fetch(`/api/admin/seller/${sellerId}/audit-log`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`
            }
        });
        
        const data = await response.json();
        const container = document.getElementById('auditLogContent');
        
        if (data.success && data.logs && data.logs.length > 0) {
            container.innerHTML = data.logs.map(log => `
                <div class="audit-log-entry">
                    <div class="timestamp">${new Date(log.created_at).toLocaleString()}</div>
                    <div class="action"><strong>${log.action}</strong></div>
                    <div class="reason">${log.reason || 'No reason provided'}</div>
                    <div style="font-size: 12px; color: #999; margin-top: 5px;">
                        By: ${log.admin_name || 'System'}
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No audit log entries found</p>';
        }
    } catch (error) {
        console.error('Error loading audit log:', error);
        document.getElementById('auditLogContent').innerHTML = '<p style="text-align: center; color: #f44336; padding: 40px;">Error loading audit log</p>';
    }
}

function hideActionForm() {
    const formDiv = document.getElementById('sellerActionForm');
    formDiv.style.display = 'none';
    formDiv.innerHTML = '';
    
    // Show the action panel buttons again
    const actionPanel = document.querySelector('#sellerActionPanel .action-panel-grid');
    if (actionPanel) {
        actionPanel.style.display = 'grid';
    }
}

// ==========================================
// RIDER ACTION PANEL FUNCTIONS
// ==========================================

function openRiderActionPanel(riderId) {
    currentRiderId = riderId;
    const rider = riders.find(r => r.id === riderId);
    if (!rider) return;
    
    // Map rider_status to status for consistency
    const riderStatus = rider.rider_status || rider.status || 'pending';
    
    const statusColors = {
        'pending': { bg: '#fff3cd', text: '#856404', border: '#ffc107' },
        'active': { bg: '#d4edda', text: '#155724', border: '#28a745' },
        'declined': { bg: '#f8d7da', text: '#721c24', border: '#dc3545' },
        'suspended': { bg: '#e2e3e5', text: '#383d41', border: '#6c757d' },
        'warning': { bg: '#fff3cd', text: '#856404', border: '#ffc107' },
        'banned': { bg: '#f8d7da', text: '#721c24', border: '#dc3545' }
    };
    const statusColor = statusColors[riderStatus] || statusColors.pending;
    
    const joinDate = new Date(rider.created_at || rider.joinDate).toLocaleString('en-US', { 
        year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    
    const infoDiv = document.getElementById('riderActionInfo');
    infoDiv.innerHTML = `
        <!-- Page Title -->
        <div style="text-align: center; margin-bottom: 35px; padding-bottom: 20px; border-bottom: 3px solid #e0e0e0;">
            <h2 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                <i class="fas fa-motorcycle" style="color: #667eea; margin-right: 10px;"></i>
                Rider Application Review
            </h2>
            <div style="margin-top: 12px;">
                <span style="display: inline-block; padding: 8px 20px; background: ${statusColor.bg}; color: ${statusColor.text}; border: 2px solid ${statusColor.border}; border-radius: 20px; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">
                    ${riderStatus.toUpperCase()}
                </span>
            </div>
        </div>

        <!-- Two-Column Grid: Rider & Vehicle Information -->
        <div style="display: grid; grid-template-columns: 480px 480px; gap: 30px; margin-bottom: 35px; justify-content: center;">
            <!-- Column 1: Rider Information -->
            <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 3px solid #667eea;">
                    <div style="background: linear-gradient(135deg, #667eea, #764ba2); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);">
                        <i class="fas fa-user" style="color: white; font-size: 20px;"></i>
                    </div>
                    <h3 style="margin: 0; color: #2d3748; font-size: 20px; font-weight: 700;">Rider Information</h3>
                </div>
                
                <div style="display: grid; gap: 20px;">
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-user-circle" style="color: #667eea;"></i> Full Name
                        </div>
                        <div style="color: #1a202c; font-size: 17px; font-weight: 600; padding-left: 24px;">${rider.first_name || ''} ${rider.last_name || ''}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-envelope" style="color: #667eea;"></i> Email
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${rider.email}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-info-circle" style="color: #667eea;"></i> Status
                        </div>
                        <div style="padding-left: 24px;">
                            <span style="display: inline-block; padding: 6px 14px; background: ${statusColor.bg}; color: ${statusColor.text}; border: 1px solid ${statusColor.border}; border-radius: 6px; font-weight: 600; font-size: 14px;">
                                ${capitalizeText(riderStatus)}
                            </span>
                        </div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-calendar-plus" style="color: #667eea;"></i> Join Date
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${joinDate}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-id-badge" style="color: #667eea;"></i> Rider ID
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">#${rider.id}</div>
                    </div>
                </div>
            </div>
            
            <!-- Column 2: Vehicle Information -->
            <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 3px solid #764ba2;">
                    <div style="background: linear-gradient(135deg, #764ba2, #667eea); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(118, 75, 162, 0.4);">
                        <i class="fas fa-motorcycle" style="color: white; font-size: 20px;"></i>
                    </div>
                    <h3 style="margin: 0; color: #2d3748; font-size: 20px; font-weight: 700;">Vehicle Information</h3>
                </div>
                
                <div style="display: grid; gap: 20px;">
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-motorcycle" style="color: #764ba2;"></i> Vehicle Type
                        </div>
                        <div style="color: #1a202c; font-size: 17px; font-weight: 600; padding-left: 24px;">${rider.vehicle_type || 'N/A'}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-id-card" style="color: #764ba2;"></i> Plate Number
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${rider.plate_number || 'Not provided'}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-phone" style="color: #764ba2;"></i> Contact Number
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${rider.contact_number || 'Not provided'}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-map-marker-alt" style="color: #764ba2;"></i> Address
                        </div>
                        <div style="color: #1a202c; font-size: 16px; padding-left: 24px;">${rider.address || 'Not provided'}</div>
                    </div>
                    
                    <div>
                        <div style="color: #718096; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px;">
                            <i class="fas fa-shield-alt" style="color: #764ba2;"></i> Verification Status
                        </div>
                        <div style="padding-left: 24px;">
                            ${rider.verified || rider.is_verified ? 
                                '<span style="display: inline-flex; align-items: center; gap: 6px; background: #d4edda; color: #155724; padding: 6px 14px; border-radius: 6px; font-size: 14px; font-weight: 600;"><i class="fas fa-check-circle"></i> Verified</span>' : 
                                '<span style="display: inline-flex; align-items: center; gap: 6px; background: #f8d7da; color: #721c24; padding: 6px 14px; border-radius: 6px; font-size: 14px; font-weight: 600;"><i class="fas fa-times-circle"></i> Not Verified</span>'
                            }
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Documents Section (Full Width Below) -->
        ${(() => {
            const documents = [];
            if (rider.driver_license) documents.push({ label: 'Driver License', path: rider.driver_license });
            if (rider.valid_id) documents.push({ label: 'Valid ID', path: rider.valid_id });
            if (rider.vehicle_or_cr) documents.push({ label: 'Vehicle OR/CR', path: rider.vehicle_or_cr });
            if (rider.profile_photo) documents.push({ label: 'Profile Photo', path: rider.profile_photo });
            
            if (documents.length > 0) {
                return `
                    <div style="background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; margin-bottom: 35px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 3px solid #28a745;">
                            <div style="background: linear-gradient(135deg, #28a745, #20c997); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);">
                                <i class="fas fa-folder-open" style="color: white; font-size: 20px;"></i>
                            </div>
                            <h3 style="margin: 0; color: #2d3748; font-size: 20px; font-weight: 700;">Uploaded Documents</h3>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px;">
                            ${documents.map(doc => `
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: white; border-radius: 8px; border: 2px solid #e9ecef; transition: all 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.05);"
                                     onmouseover="this.style.borderColor='#667eea'; this.style.boxShadow='0 4px 12px rgba(102,126,234,0.2)'"
                                     onmouseout="this.style.borderColor='#e9ecef'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.05)'">
                                    <span style="font-size: 14px; color: #2d3748; font-weight: 600; display: flex; align-items: center; gap: 10px;">
                                        <i class="fas fa-file-alt" style="color: #667eea; font-size: 18px;"></i>
                                        ${doc.label}
                                    </span>
                                    <a href="/uploads/${doc.path}" target="_blank" 
                                       style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px; transition: all 0.2s; box-shadow: 0 2px 8px rgba(102,126,234,0.3);"
                                       onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(102,126,234,0.4)'"
                                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(102,126,234,0.3)'">
                                        <i class="fas fa-eye"></i> View
                                    </a>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else {
                return `
                    <div style="background: linear-gradient(135deg, #fff3cd, #ffeeba); padding: 25px; border-radius: 12px; border: 2px solid #ffc107; margin-bottom: 35px; box-shadow: 0 4px 12px rgba(255,193,7,0.2); text-align: center;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 12px;">
                            <i class="fas fa-exclamation-triangle" style="color: #856404; font-size: 28px;"></i>
                            <p style="margin: 0; color: #856404; font-size: 16px; font-weight: 600;">No documents uploaded yet</p>
                        </div>
                    </div>
                `;
            }
        })()}

        <!-- Action Buttons Section - Dynamic Based on Status -->
        ${(riderStatus === 'pending') ? `
        <div style="clear: both; width: 100%; background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <h3 style="margin: 0 0 20px 0; color: #2d3748; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-clipboard-check" style="color: #667eea;"></i> Pending Rider Actions
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;">
                <button onclick="approveRider()" 
                        style="background: linear-gradient(135deg, #28a745, #20c997); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);"
                        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(40, 167, 69, 0.4)';"
                        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(40, 167, 69, 0.3)';"
                        title="Approve this rider application">
                    <i class="fas fa-check-circle"></i> Approve Rider
                </button>
                
                <button onclick="declineRider()" 
                        style="background: linear-gradient(135deg, #dc3545, #c82333); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);"
                        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(220, 53, 69, 0.4)';"
                        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(220, 53, 69, 0.3)';"
                        title="Decline this rider application">
                    <i class="fas fa-times-circle"></i> Decline Rider
                </button>
                
                <button onclick="requestRiderReSubmission()" 
                        style="background: linear-gradient(135deg, #007bff, #0056b3); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);"
                        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(0, 123, 255, 0.4)';"
                        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0, 123, 255, 0.3)';"
                        title="Request re-submission of application">
                    <i class="fas fa-redo"></i> Request Re-Submission
                </button>
            </div>
        </div>
        ` : (riderStatus === 'declined') ? `
        <div style="clear: both; width: 100%; background: linear-gradient(135deg, #f8d7da, #f5c6cb); padding: 25px; border-radius: 12px; border: 2px solid #f5c6cb; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(220, 53, 69, 0.2); text-align: center;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 15px;">
                <i class="fas fa-ban" style="color: #721c24; font-size: 32px;"></i>
                <h3 style="margin: 0; color: #721c24; font-size: 20px; font-weight: 700;">Status: Declined</h3>
            </div>
            <p style="margin: 0; color: #721c24; font-size: 14px; font-weight: 500;">This rider application has been declined. No admin actions available.</p>
        </div>
        ` : `
        <div id="riderAdminActionsSection" style="clear: both; width: 100%; background: linear-gradient(135deg, #f8f9fa, #ffffff); padding: 25px; border-radius: 12px; border: 2px solid #e9ecef; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <h3 style="margin: 0 0 20px 0; color: #2d3748; font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-tools" style="color: #667eea;"></i> Admin Actions
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px;">
                <button onclick="showRiderWarningForm()" 
                        style="background: linear-gradient(135deg, #ffc107, #ffb300); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);"
                        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 193, 7, 0.4)';"
                        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 193, 7, 0.3)';"
                        title="Issue a warning to the rider">
                    <i class="fas fa-exclamation-triangle"></i> Warning
                </button>
                
                <button onclick="showRiderSuspensionForm()" 
                        style="background: linear-gradient(135deg, #ff9800, #f57c00); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3);"
                        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 152, 0, 0.4)';"
                        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 152, 0, 0.3)';"
                        title="Temporarily suspend the rider's account">
                    <i class="fas fa-pause-circle"></i> Suspension
                </button>
                
                <button onclick="showRiderBanForm()" 
                        style="background: linear-gradient(135deg, #dc3545, #c82333); color: white; border: none; padding: 14px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);"
                        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(220, 53, 69, 0.4)';"
                        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(220, 53, 69, 0.3)';"
                        title="Permanently ban the rider from the platform">
                    <i class="fas fa-gavel"></i> Permanent Ban
                </button>
            </div>
        </div>
        `}
    `;
    
    document.getElementById('riderActionForm').style.display = 'none';
    document.getElementById('riderActionForm').innerHTML = '';
    document.getElementById('riderActionPanel').style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Show action panel buttons if they exist
    const actionPanel = document.querySelector('#riderActionPanel .action-panel-grid');
    if (actionPanel) {
        actionPanel.style.display = 'grid';
    }
}

function closeRiderActionPanel() {
    document.getElementById('riderActionPanel').style.display = 'none';
    document.body.style.overflow = '';
    currentRiderId = null;
}

function showRiderWarningForm() {
    const formDiv = document.getElementById('riderActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container" style="background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); width: 100%; display: block;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: #ff9800; margin: 0; font-size: 20px; font-weight: 600;">
                    <i class="fas fa-exclamation-triangle"></i> Issue Warning
                </h3>
                <button onclick="hideRiderActionForm()" style="background: none; border: none; font-size: 24px; color: #999; cursor: pointer; padding: 0; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center;">&times;</button>
            </div>
            <div class="form-group" style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Warning Type *</label>
                <select id="riderWarningType" class="form-control" style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px;">
                    <option value="late_delivery">Late Delivery</option>
                    <option value="customer_complaint">Customer Complaint</option>
                    <option value="unsafe_driving">Unsafe Driving</option>
                    <option value="policy_violation">Policy Violation</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div class="form-group" style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Warning Message *</label>
                <textarea id="riderWarningMessage" placeholder="Enter detailed warning message..." required style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px; font-family: inherit; resize: vertical; min-height: 120px;"></textarea>
            </div>
            <div class="form-actions" style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 25px;">
                <button class="btn btn-secondary" onclick="hideRiderActionForm()" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">Cancel</button>
                <button class="btn" onclick="submitRiderWarning()" style="padding: 10px 20px; background: #ff9800; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600;">Issue Warning</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    formDiv.style.width = '100%';
    formDiv.style.clear = 'both';
    formDiv.style.marginTop = '20px';
}

function showRiderSuspensionForm() {
    const formDiv = document.getElementById('riderActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container" style="width: 100%; display: block;">
            <h3 style="color: #ff5722; margin-bottom: 15px;">
                <i class="fas fa-pause-circle"></i> Suspend Account
            </h3>
            <div class="form-group">
                <label>Suspension Duration</label>
                <select id="riderSuspensionDuration" class="form-control">
                    <option value="1">1 Day</option>
                    <option value="3">3 Days</option>
                    <option value="7">7 Days</option>
                    <option value="14">14 Days</option>
                    <option value="30">30 Days</option>
                    <option value="custom">Custom</option>
                </select>
            </div>
            <div class="form-group" id="riderCustomDurationGroup" style="display: none;">
                <label>Custom Days</label>
                <input type="number" id="riderCustomDuration" min="1" placeholder="Enter number of days">
            </div>
            <div class="form-group">
                <label>Suspension Reason *</label>
                <textarea id="riderSuspensionReason" placeholder="Enter reason for suspension..." required></textarea>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideRiderActionForm()">Cancel</button>
                <button class="btn btn-danger" onclick="submitRiderSuspension()">Suspend Rider</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    formDiv.style.width = '100%';
    formDiv.style.clear = 'both';
    formDiv.style.marginTop = '20px';
    
    document.getElementById('riderSuspensionDuration').addEventListener('change', (e) => {
        document.getElementById('riderCustomDurationGroup').style.display = e.target.value === 'custom' ? 'block' : 'none';
    });
}

function showRiderBanForm() {
    const formDiv = document.getElementById('riderActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container" style="border: 2px solid #f44336; width: 100%; display: block;">
            <h3 style="color: #f44336; margin-bottom: 15px;">
                <i class="fas fa-times-circle"></i> Permanent Ban
            </h3>
            <div style="background: #ffebee; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
                <p style="margin: 0; color: #c62828; font-weight: 600;">
                    ⚠️ WARNING: This action is permanent and cannot be undone!
                </p>
                <p style="margin: 10px 0 0 0; color: #c62828;">
                    The rider will be immediately blocked from accessing the platform and all their deliveries will be cancelled.
                </p>
            </div>
            <div class="form-group">
                <label>Ban Reason *</label>
                <textarea id="riderBanReason" placeholder="Enter detailed reason for permanent ban..." required></textarea>
            </div>
            <div class="form-group">
                <label style="display: flex; align-items: center; gap: 10px;">
                    <input type="checkbox" id="riderConfirmBan" style="width: auto;">
                    <span>I understand this action is permanent and irreversible</span>
                </label>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideRiderActionForm()">Cancel</button>
                <button class="btn btn-danger" onclick="submitRiderBan()">Permanently Ban Rider</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    formDiv.style.width = '100%';
    formDiv.style.clear = 'both';
    formDiv.style.marginTop = '20px';
}

function viewRiderAuditLog() {
    const formDiv = document.getElementById('riderActionForm');
    formDiv.innerHTML = `
        <div class="action-form-container">
            <h3 style="color: #2196f3; margin-bottom: 15px;">
                <i class="fas fa-history"></i> Audit Log
            </h3>
            <div id="riderAuditLogContent" style="max-height: 400px; overflow-y: auto;">
                <p style="text-align: center; color: #999; padding: 40px;">
                    <i class="fas fa-spinner fa-spin" style="font-size: 24px;"></i><br><br>
                    Loading audit log...
                </p>
            </div>
            <div class="form-actions">
                <button class="btn btn-secondary" onclick="hideRiderActionForm()">Close</button>
            </div>
        </div>
    `;
    formDiv.style.display = 'block';
    
    // Load audit log
    loadRiderAuditLog(currentRiderId);
}

// Rider Submit functions
async function submitRiderWarning() {
    const warningType = document.getElementById('riderWarningType').value;
    const message = document.getElementById('riderWarningMessage').value.trim();
    
    if (!message) {
        showNotification('Please enter a warning message', 'error');
        return;
    }
    
    if (!currentRiderId) {
        showNotification('No rider selected', 'error');
        return;
    }
    
    showRiderWarningConfirmationModal(() => {
        executeRiderWarning(warningType, message);
    });
}

async function executeRiderWarning(warningType, message) {
    try {
        const reason = `${warningType}: ${message}`;
        const response = await authFetch(`/api/admin/riders/${currentRiderId}/status`, {
            method: 'PUT',
            body: JSON.stringify({
                status: 'warning',
                reason: reason
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('⚠️ Warning issued successfully', 'success');
            // Update the rider in the array immediately
            const riderIndex = riders.findIndex(r => r.id === currentRiderId);
            if (riderIndex !== -1) {
                riders[riderIndex].rider_status = 'warning';
                // Re-render table immediately to show updated status
                renderRidersTable();
            }
            // Hide action form and refresh rider data
            const actionForm = document.getElementById('riderActionForm');
            if (actionForm) {
                actionForm.style.display = 'none';
                actionForm.innerHTML = '';
            }
            // Show the action panel buttons again
            const actionPanel = document.querySelector('#riderActionPanel .action-panel-grid');
            if (actionPanel) {
                actionPanel.style.display = 'grid';
            }
            // Reload rider details and table with a small delay to ensure DB commit
            if (currentRiderId) {
                setTimeout(() => {
                    viewRiderDetails(currentRiderId);
                }, 500);
            }
            setTimeout(() => {
                loadRidersData();
            }, 500);
        } else {
            showNotification(data.message || data.error || 'Failed to issue warning', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('An error occurred while issuing warning', 'error');
    }
}

async function submitRiderSuspension() {
    let duration = document.getElementById('riderSuspensionDuration').value;
    if (duration === 'custom') {
        duration = document.getElementById('riderCustomDuration').value;
    }
    const reason = document.getElementById('riderSuspensionReason').value.trim();

    // Validate rider selection
    if (!currentRiderId) {
        showNotification('No rider selected', 'error');
        return;
    }
    // Validate reason
    if (!reason) {
        showNotification('Please enter a suspension reason', 'error');
        return;
    }
    // Validate duration
    const durationInt = parseInt(duration, 10);
    if (isNaN(durationInt) || durationInt <= 0) {
        showNotification('Please specify a valid suspension duration in days', 'error');
        return;
    }
    
    showRiderSuspensionConfirmationModal(duration, () => {
        executeRiderSuspension(durationInt, reason);
    });
}

async function executeRiderSuspension(durationInt, reason) {
    try {
        const response = await authFetch(`/api/admin/riders/${currentRiderId}/status`, {
            method: 'PUT',
            body: JSON.stringify({
                status: 'suspended',
                reason: reason,
                duration_days: durationInt
            })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification(`⏸️ Rider suspended successfully for ${durationInt} day(s)`, 'success');
            // Update the rider in the array immediately
            const riderIndex = riders.findIndex(r => r.id === currentRiderId);
            if (riderIndex !== -1) {
                riders[riderIndex].rider_status = 'suspended';
                // Re-render table immediately to show updated status
                renderRidersTable();
            }
            // Hide action form and refresh rider data
            const actionForm = document.getElementById('riderActionForm');
            if (actionForm) {
                actionForm.style.display = 'none';
                actionForm.innerHTML = '';
            }
            // Show the action panel buttons again
            const actionPanel = document.querySelector('#riderActionPanel .action-panel-grid');
            if (actionPanel) {
                actionPanel.style.display = 'grid';
            }
            // Close modal first
            closeRiderActionPanel();
            // Reload rider details and table with a small delay to ensure DB commit
            setTimeout(() => {
                loadRidersData();
            }, 500);
        } else {
            showNotification(data.message || data.error || 'Failed to suspend rider', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('An error occurred while suspending rider', 'error');
    }
}

async function submitRiderBan() {
    const reason = document.getElementById('riderBanReason').value.trim();
    const confirmed = document.getElementById('riderConfirmBan').checked;
    
    // Validate rider selection
    if (!currentRiderId) {
        showNotification('No rider selected', 'error');
        return;
    }
    if (!reason) {
        showNotification('Please enter a reason for the ban', 'error');
        return;
    }
    
    if (!confirmed) {
        showNotification('Please confirm you understand this action is permanent', 'error');
        return;
    }
    
    showRiderBanConfirmationModal(() => {
        executeRiderBan(reason);
    });
}

async function executeRiderBan(reason) {
    try {
        console.log('🔨 Banning rider:', currentRiderId, 'Reason:', reason);
        const response = await authFetch(`/api/admin/riders/${currentRiderId}/status`, {
            method: 'PUT',
            body: JSON.stringify({
                status: 'banned',
                reason: reason
            })
        });
        
        const data = await response.json();
        console.log('Ban response:', data);
        
        if (data.success) {
            showNotification('🔨 Rider banned permanently', 'success');
            // Update the rider in the array immediately
            const riderIndex = riders.findIndex(r => r.id === currentRiderId);
            if (riderIndex !== -1) {
                riders[riderIndex].rider_status = 'banned';
                // Re-render table immediately to show updated status
                renderRidersTable();
            }
            // Hide action form and refresh rider data
            const actionForm = document.getElementById('riderActionForm');
            if (actionForm) {
                actionForm.style.display = 'none';
                actionForm.innerHTML = '';
            }
            // Show the action panel buttons again
            const actionPanel = document.querySelector('#riderActionPanel .action-panel-grid');
            if (actionPanel) {
                actionPanel.style.display = 'grid';
            }
            // Close modal first
            closeRiderActionPanel();
            // Don't reload automatically - just update the table with the new status
            // The status is already updated in the riders array, so just re-render
            renderRidersTable();
            
            // Optionally reload in the background after a delay, but don't block UI
            setTimeout(async () => {
                try {
                    console.log('🔄 Reloading riders data after ban (background)...');
                    await loadRidersData();
                } catch (error) {
                    console.error('Error reloading riders data:', error);
                    // Don't show error to user - the status is already updated locally
                }
            }, 2000);
        } else {
            console.error('Ban failed:', data);
            showNotification(data.message || data.error || 'Failed to ban rider', 'error');
        }
    } catch (error) {
        console.error('Error banning rider:', error);
        showNotification('An error occurred while banning rider: ' + error.message, 'error');
    }
}

async function loadRiderAuditLog(riderId) {
    try {
        const response = await fetch(`/api/admin/rider/${riderId}/audit-log`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`
            }
        });
        
        const data = await response.json();
        const container = document.getElementById('riderAuditLogContent');
        
        if (data.success && data.logs && data.logs.length > 0) {
            container.innerHTML = data.logs.map(log => `
                <div class="audit-log-entry">
                    <div class="timestamp">${new Date(log.created_at).toLocaleString()}</div>
                    <div class="action"><strong>${log.action}</strong></div>
                    <div class="reason">${log.reason || 'No reason provided'}</div>
                    <div style="font-size: 12px; color: #999; margin-top: 5px;">
                        By: ${log.admin_name || 'System'}
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No audit log entries found</p>';
        }
    } catch (error) {
        console.error('Error loading audit log:', error);
        document.getElementById('riderAuditLogContent').innerHTML = '<p style="text-align: center; color: #f44336; padding: 40px;">Error loading audit log</p>';
    }
}

function hideRiderActionForm() {
    document.getElementById('riderActionForm').style.display = 'none';
    document.getElementById('riderActionForm').innerHTML = '';
}

// Pending Rider Actions
async function approveRider() {
    if (!currentRiderId) {
        notify.error('No rider selected');
        return;
    }
    
    if (!confirm('Are you sure you want to approve this rider application?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/riders/${currentRiderId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`
            }
        });
        
        const data = await response.json();
        if (data.success) {
            notify.success('Rider approved successfully');
            closeRiderActionPanel();
            loadRidersData();
        } else {
            notify.error(data.message || 'Failed to approve rider');
        }
    } catch (error) {
        console.error('Error:', error);
        notify.error('An error occurred');
    }
}

async function declineRider() {
    if (!currentRiderId) {
        notify.error('No rider selected');
        return;
    }
    
    showMissingRequirementsModal('rider', currentRiderId);
}

async function requestRiderReSubmission() {
    if (!currentRiderId) {
        notify.error('No rider selected');
        return;
    }
    
    const message = prompt('Please enter a message explaining what needs to be corrected:');
    if (!message || message.trim() === '') {
        notify.error('Re-submission message is required');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/riders/${currentRiderId}/request-resubmission`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`
            },
            body: JSON.stringify({ message: message.trim() })
        });
        
        const data = await response.json();
        if (data.success) {
            notify.success('Re-submission request sent to rider');
            closeRiderActionPanel();
        } else {
            notify.error(data.message || 'Failed to send re-submission request');
        }
    } catch (error) {
        console.error('Error:', error);
        notify.error('An error occurred');
    }
}

async function requestSellerDocuments() {
    if (!currentSellerId) {
        notify.error('No seller selected');
        return;
    }
    
    const message = prompt('Please enter a message explaining what documents are needed:');
    if (!message || message.trim() === '') {
        notify.error('Document request message is required');
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/sellers/${currentSellerId}/request-documents`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`
            },
            body: JSON.stringify({ message: message.trim() })
        });
        
        const data = await response.json();
        if (data.success) {
            notify.success('Document request sent to seller');
            closeSellerReviewModal();
        } else {
            notify.error(data.message || 'Failed to send document request');
        }
    } catch (error) {
        console.error('Error:', error);
        notify.error('An error occurred');
    }
}

// Decline Seller with Missing Requirements Modal
function declineSeller() {
    if (!currentSellerId) {
        notify.error('No seller selected');
        return;
    }
    
    showMissingRequirementsModal('seller', currentSellerId);
}

// Decline Rider with Missing Requirements Modal
function declineRider() {
    if (!currentRiderId) {
        notify.error('No rider selected');
        return;
    }
    
    showMissingRequirementsModal('rider', currentRiderId);
}

// Show Missing Requirements Selection Modal
function showMissingRequirementsModal(userType, userId) {
    const modal = document.createElement('div');
    modal.id = 'missingRequirementsModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    const requirements = userType === 'seller' ? [
        { id: 'valid_id', label: 'Valid ID (Government-issued)' },
        { id: 'business_permit', label: 'Business Permit' },
        { id: 'address_proof', label: 'Proof of Address' },
        { id: 'profile_photo', label: 'Profile Photo' },
        { id: 'store_logo', label: 'Store Logo' },
        { id: 'other', label: 'Other (specify below)' }
    ] : [
        { id: 'valid_id', label: 'Valid ID (Government-issued)' },
        { id: 'driver_license', label: 'Driver\'s License' },
        { id: 'vehicle_or_cr', label: 'Vehicle OR/CR' },
        { id: 'profile_photo', label: 'Profile Photo' },
        { id: 'address_proof', label: 'Proof of Address' },
        { id: 'other', label: 'Other (specify below)' }
    ];
    
    modal.innerHTML = `
        <div style="background: white; border-radius: 16px; max-width: 600px; width: 90%; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            <div style="background: linear-gradient(135deg, #e74c3c, #c0392b); color: white; padding: 25px; border-radius: 16px 16px 0 0;">
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                    <div style="width: 50px; height: 50px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-exclamation-triangle" style="font-size: 24px;"></i>
                    </div>
                    <div>
                        <h2 style="margin: 0; font-size: 24px;">Decline ${userType === 'seller' ? 'Seller' : 'Rider'} Application</h2>
                        <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">Select missing requirements</p>
                    </div>
                </div>
            </div>
            
            <div style="padding: 30px;">
                <div style="margin-bottom: 25px;">
                    <label style="display: block; margin-bottom: 15px; color: #2c3e50; font-weight: 600; font-size: 15px;">
                        <i class="fas fa-clipboard-list"></i> Missing Requirements *
                    </label>
                    <div id="requirementsList" style="display: flex; flex-direction: column; gap: 12px;">
                        ${requirements.map(req => `
                            <label style="display: flex; align-items: center; gap: 12px; padding: 14px; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; transition: all 0.2s;" 
                                   onmouseover="this.style.borderColor='#667eea'; this.style.background='#f8f9ff';"
                                   onmouseout="this.style.borderColor='#e0e0e0'; this.style.background='white';">
                                <input type="checkbox" name="missing_req" value="${req.id}" 
                                       style="width: 20px; height: 20px; cursor: pointer; accent-color: #667eea;">
                                <span style="flex: 1; color: #2c3e50; font-size: 14px; font-weight: 500;">${req.label}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
                
                <div style="margin-bottom: 25px;">
                    <label style="display: block; margin-bottom: 10px; color: #2c3e50; font-weight: 600; font-size: 15px;">
                        <i class="fas fa-comment-alt"></i> Additional Notes (Optional)
                    </label>
                    <textarea id="declineReason" rows="4" 
                              style="width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-family: inherit; font-size: 14px; resize: vertical; transition: border-color 0.3s;"
                              placeholder="Enter any additional information or instructions..."
                              onfocus="this.style.borderColor='#667eea'"
                              onblur="this.style.borderColor='#e0e0e0'"></textarea>
                </div>
                
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button onclick="closeMissingRequirementsModal()" 
                            style="padding: 12px 24px; background: #ecf0f1; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; color: #7f8c8d; transition: all 0.3s;"
                            onmouseover="this.style.background='#bdc3c7'"
                            onmouseout="this.style.background='#ecf0f1'">
                        Cancel
                    </button>
                    <button onclick="confirmDecline('${userType}', ${userId})" 
                            style="padding: 12px 24px; background: linear-gradient(135deg, #e74c3c, #c0392b); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; transition: all 0.3s; box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(231, 76, 60, 0.4)'"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(231, 76, 60, 0.3)'">
                        <i class="fas fa-check"></i> Confirm Decline
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
}

function closeMissingRequirementsModal() {
    const modal = document.getElementById('missingRequirementsModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}

async function confirmDecline(userType, userId) {
    const checkboxes = document.querySelectorAll('input[name="missing_req"]:checked');
    const missingRequirements = Array.from(checkboxes).map(cb => cb.nextElementSibling.textContent.trim());
    
    if (missingRequirements.length === 0) {
        notify.error('Please select at least one missing requirement');
        return;
    }
    
    const reason = document.getElementById('declineReason').value.trim() || 'Missing requirements selected above';
    
    const endpoint = userType === 'seller' 
        ? `/api/admin/sellers/${userId}/decline`
        : `/api/admin/riders/${userId}/decline`;
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`
            },
            body: JSON.stringify({
                missing_requirements: missingRequirements,
                reason: reason
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            notify.success(`${userType === 'seller' ? 'Seller' : 'Rider'} application declined. Notification sent.`);
            closeMissingRequirementsModal();
            
            if (userType === 'seller') {
                closeSellerReviewModal();
                loadSellersData();
            } else {
                closeRiderActionPanel();
                loadRidersData();
            }
        } else {
            notify.error(data.message || 'Failed to decline application');
        }
    } catch (error) {
        console.error('Error:', error);
        notify.error('An error occurred');
    }
}

// Expose functions globally
window.openSellerActionPanel = openSellerActionPanel;
window.closeSellerActionPanel = closeSellerActionPanel;
window.openRiderActionPanel = openRiderActionPanel;
window.closeRiderActionPanel = closeRiderActionPanel;

