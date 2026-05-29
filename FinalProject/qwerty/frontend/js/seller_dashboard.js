// Seller Dashboard JS
// Use existing global API_BASE if already defined by another script to avoid redeclaration SyntaxError
// Fallback to origin-based default
if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = window.location.origin;
}
if (typeof API_BASE === 'undefined') {
    var API_BASE = window.API_BASE;
}

// PSGC Location API for cascading dropdowns (avoid redeclaration if defined elsewhere)
if (typeof window.PSGC_API === 'undefined') {
    window.PSGC_API = 'https://psgc.gitlab.io/api';
}
// Store cache variables removed - multi-store functionality removed

let sellerData = {};
let products = [];
let orders = [];

// Auth fetch helper for authenticated API requests
async function authFetch(url, options = {}) {
    const token = localStorage.getItem('hub_access_token');
    
    if (!token) {
        console.warn('No authentication token found. Redirecting to login...');
        window.location.href = '/loginregister.html';
        throw new Error('Not authenticated');
    }
    
    // Get current store ID (check both local variable and window property)
    // No store_id handling - single store per seller
    let finalUrl = url;
    
    const headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };
    
    // Don't set Content-Type for FormData (browser will set it with boundary)
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }
    
    const response = await fetch(API_BASE + finalUrl, {
        ...options,
        headers
    });
    
    // Handle 401 Unauthorized - token expired or invalid
    if (response.status === 401) {
        console.warn('Authentication failed. Token may be expired. Redirecting to login...');
        localStorage.removeItem('hub_access_token');
        window.location.href = '/loginregister.html';
        throw new Error('Unauthorized');
    }
    
    return response;
}

// Simple notification system
const notify = {
    success: function(message) {
        this.show(message, 'success');
    },
    error: function(message) {
        this.show(message, 'error');
    },
    info: function(message) {
        this.show(message, 'info');
    },
    show: function(message, type) {
        // Remove existing notifications
        const existing = document.querySelectorAll('.notification-toast');
        existing.forEach(n => n.remove());
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification-toast notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fa ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Trigger animation
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
};

// Expose data loading functions globally for inline switchSection to call
window.loadDashboardData = loadDashboardData;
window.loadOrders = loadOrders;
window.loadProducts = loadProducts;
window.loadEarnings = loadEarnings;

// =====================================================================
// RETURNS & REFUNDS SECTION
// =====================================================================

let returnRequests = [];
let currentReturnFilter = 'all';

async function loadReturnRequests() {
    try {
        const response = await authFetch('/api/sellers/return-refund-requests');
        if (!response.ok) throw new Error('Failed to load return/refund requests');

        const data = await response.json();
        returnRequests = data.data?.requests || data.requests || [];
        
        // Update badge count
        const pendingCount = returnRequests.filter(r => r.seller_response === 'pending' || r.status === 'pending').length;
        const badge = document.getElementById('returnsBadge');
        if (badge) {
            if (pendingCount > 0) {
                badge.textContent = pendingCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
        
        renderReturnRequests(returnRequests);
    } catch (error) {
        console.error('Error loading return requests:', error);
        const tbody = document.getElementById('returnRequestsTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: #ef4444;">
                        <i class="fa-solid fa-exclamation-circle" style="font-size: 48px; margin-bottom: 16px;"></i>
                        <p>Failed to load return/refund requests. Please try again later.</p>
                    </td>
                </tr>
            `;
        }
    }
}

function filterReturnRequests(filter) {
    currentReturnFilter = filter;
    
    // Update filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.textContent.trim() === filter.charAt(0).toUpperCase() + filter.slice(1) || 
            (filter === 'all' && btn.textContent.trim() === 'All')) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    let filtered = returnRequests;
    if (filter !== 'all') {
        if (filter === 'pending') {
            filtered = returnRequests.filter(r => r.seller_response === 'pending' || r.status === 'pending');
        } else if (filter === 'approved') {
            filtered = returnRequests.filter(r => r.seller_response === 'approved');
        } else if (filter === 'rejected') {
            filtered = returnRequests.filter(r => r.seller_response === 'rejected');
        } else if (filter === 'processing') {
            filtered = returnRequests.filter(r => r.status === 'processing');
        } else if (filter === 'completed') {
            filtered = returnRequests.filter(r => r.status === 'completed');
        }
    }
    
    renderReturnRequests(filtered);
}

function renderReturnRequests(requests) {
    const tbody = document.getElementById('returnRequestsTableBody');
    if (!tbody) return;

    if (requests.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 40px;">
                    <i class="fa-solid fa-inbox" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                    <p style="color: #666;">No return/refund requests found.</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = requests.map(req => {
        const statusColor = getReturnStatusColor(req.seller_response || req.status);
        const statusText = formatReturnStatus(req);
        const createdDate = new Date(req.created_at);
        
        return `
            <tr>
                <td>#${req.id}</td>
                <td>#${req.order_id}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        ${req.product_image ? `<img src="${req.product_image.startsWith('http') ? req.product_image : 'http://127.0.0.1:5000' + req.product_image}" 
                             style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" 
                             onerror="this.src='https://via.placeholder.com/40'">` : ''}
                        <span>${req.product_name || 'Product'}</span>
                    </div>
                </td>
                <td>
                    <div>
                        <strong>${req.customer_name || (req.customer_first_name && req.customer_last_name ? `${req.customer_first_name} ${req.customer_last_name}` : 'Customer')}</strong><br>
                        <small style="color: #666;">${req.customer_phone || req.customer_email || ''}</small>
                    </div>
                </td>
                <td><span class="status-badge" style="background: #e3f2fd; color: #1976d2;">${req.request_type.charAt(0).toUpperCase() + req.request_type.slice(1)}</span></td>
                <td>
                    <div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${req.reason || ''}">
                        ${req.reason || 'N/A'}
                    </div>
                </td>
                <td>
                    <span class="status-badge" style="background: ${statusColor}20; color: ${statusColor}; border: 1px solid ${statusColor};">
                        ${statusText}
                    </span>
                </td>
                <td>${createdDate.toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="viewReturnRequestDetails(${req.id})" title="View Details">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function getReturnStatusColor(status) {
    const statusMap = {
        'pending': '#ffc107',
        'approved': '#28a745',
        'rejected': '#dc3545',
        'processing': '#17a2b8',
        'completed': '#28a745',
        'request_info': '#ff9800'
    };
    return statusMap[status] || '#6c757d';
}

function formatReturnStatus(request) {
    if (request.status === 'completed' || request.refund_processed_at) {
        return 'Refund Completed';
    } else if (request.status === 'processing') {
        return 'Refund Processing';
    } else if (request.seller_response === 'approved' || request.status === 'approved') {
        if (request.request_type === 'return' || request.request_type === 'both') {
            if (request.item_received_at) {
                return 'Item Received - Awaiting Refund';
            } else if (request.pickup_completed_at) {
                return 'Item Picked Up - Returning to Seller';
            } else if (request.pickup_rider_id) {
                return 'Pickup Scheduled - Rider Assigned';
            }
            return 'Approved - Awaiting Rider Pickup';
        } else {
            // Refund-only request
            return 'Approved - Refund Processing';
        }
    } else if (request.seller_response === 'rejected' || request.status === 'rejected') {
        return 'Rejected';
    } else if (request.seller_response === 'request_info') {
        return 'More Info Requested';
    }
    return 'Pending Review';
}

// ============================
// Sales & Discounts (Seller)
// ============================
function openDiscountModal() {
    loadSellerProductsForDiscounts();
    const modal = document.getElementById('discountModal');
    if (modal) {
        modal.style.display = 'block';
        if (document && document.body) {
            document.body.classList.add('modal-open');
        }
    }
}

async function loadSellerProductsForDiscounts() {
    try {
        const resp = await authFetch('/api/sellers/products');
        const data = await resp.json();
        const items = data.data || data || [];
        const container = document.getElementById('discProducts');
        if (!container) return;
        container.innerHTML = items.map(p => `
            <label class="checkbox">
                <input type="checkbox" value="${p.id}"> ${p.title || p.name || ('Product #' + p.id)}
            </label>
        `).join('');
    } catch (e) {
        console.error('Failed loading seller products:', e);
    }
}

function gatherSelectedProductIds() {
    const container = document.getElementById('discProducts');
    if (!container) return [];
    return Array.from(container.querySelectorAll('input[type="checkbox"]:checked'))
        .map(el => parseInt(el.value, 10))
        .filter(v => !isNaN(v));
}

async function submitDiscount() {
    try {
        const name = document.getElementById('discName').value.trim();
        const description = document.getElementById('discDescription').value.trim();
        const discount_type = document.getElementById('discType').value;
        const value = parseFloat(document.getElementById('discValue').value);
        const start_at_local = document.getElementById('discStart').value;
        const end_at_local = document.getElementById('discEnd').value;
        const product_ids = gatherSelectedProductIds();

        if (!name || product_ids.length === 0 || !start_at_local || !end_at_local || !(value > 0)) {
            notify.error('Please fill out all required fields and select products.');
            return;
        }
        const start_at = new Date(start_at_local).toISOString();
        const end_at = new Date(end_at_local).toISOString();

        const resp = await authFetch('/api/seller/discount', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, discount_type, value, start_at, end_at, product_ids })
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
            notify.success('Discount submitted for approval');
            closeModal('discountModal');
            loadMyDiscounts();
        } else {
            notify.error(data.error || 'Failed to submit discount');
        }
    } catch (e) {
        console.error('Submit discount error:', e);
        notify.error('Error submitting discount');
    }
}

async function loadMyDiscounts() {
    try {
        const resp = await authFetch('/api/seller/discounts');
        const data = await resp.json();
        const items = data.data || data || [];
        const tbody = document.querySelector('#discountsTable tbody');
        if (!tbody) return;
        tbody.innerHTML = items.map(d => {
            const val = Number(d.value || 0);
            const valueText = d.discount_type === 'percent' ? `${val}%` : `₱${val.toFixed(2)}`;
            const prods = Array.isArray(d.product_ids) ? d.product_ids.join(', ') : '';
            return `<tr>
                <td>${d.name || ''}</td>
                <td>${d.discount_type || ''}</td>
                <td>${valueText}</td>
                <td>${prods}</td>
                <td>${d.start_at || ''}</td>
                <td>${d.end_at || ''}</td>
                <td>${d.status || 'pending'}</td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('Load discounts error:', e);
    }
}

async function viewReturnRequestDetails(requestId) {
    const request = returnRequests.find(r => r.id === requestId);
    if (!request) {
        notify.error('Request not found');
        return;
    }

    // Create and show modal
    showReturnRequestModal(request);
}

function showReturnRequestModal(request) {
    // Remove existing modal if any
    const existingModal = document.getElementById('returnRequestModal');
    if (existingModal) existingModal.remove();

    const statusColor = getReturnStatusColor(request.seller_response || request.status);
    const statusText = formatReturnStatus(request);
    const requestTypeIcon = request.request_type === 'return' ? 'fa-rotate-left' : request.request_type === 'refund' ? 'fa-money-bill-wave' : 'fa-exchange-alt';
    const requestTypeColor = request.request_type === 'return' ? '#17a2b8' : request.request_type === 'refund' ? '#28a745' : '#ff9800';
    
    const modalHTML = `
        <div id="returnRequestModal" class="modal" style="display: block;">
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
                        <button onclick="refreshReturnRequest(${request.id})" class="modal-close-modern" style="width: 36px; height: 36px; border-radius: 8px; background: rgba(255,255,255,0.15); display: flex; align-items: center; justify-content: center; font-size: 16px; padding: 0;" title="Refresh" aria-label="Refresh">
                            <i class="fa-solid fa-rotate"></i>
                        </button>
                        <button class="modal-close-modern" aria-label="Close" onclick="closeReturnRequestModal()">&times;</button>
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
                                        <div style="font-weight: 600; color: var(--text-color); margin-bottom: 4px;">Refund Processed</div>
                                        <div style="color: var(--text-light); font-size: 13px;">${new Date(request.refund_processed_at).toLocaleString('en-US', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                ${request.seller_response === 'pending' || (request.seller_response === 'approved' && (request.request_type === 'return' || request.request_type === 'both') && request.pickup_completed_at && !request.item_received_at) || (request.status === 'processing' && request.seller_response === 'approved' && !request.refund_processed_at) ? `
                    <div class="modal-actions-modern">
                        ${request.seller_response === 'pending' ? `
                            <button class="btn btn-cancel-modern" onclick="closeReturnRequestModal()">
                                <i class="fa fa-times"></i> Close
                            </button>
                            <button class="btn btn-save-modern" style="background: #10b981;" onclick="respondToReturnRequest(${request.id}, 'approved')">
                                <i class="fa fa-check"></i> Approve
                            </button>
                            <button class="btn" style="background: #ef4444; color: white; padding: 10px 22px; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; box-shadow: 0 6px 12px rgba(239, 68, 68, 0.3);" onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 8px 16px rgba(239, 68, 68, 0.35)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 6px 12px rgba(239, 68, 68, 0.3)'" onclick="respondToReturnRequest(${request.id}, 'rejected')">
                                <i class="fa fa-times"></i> Reject
                            </button>
                            <button class="btn" style="background: #f59e0b; color: white; padding: 10px 22px; border: none; border-radius: 8px; font-size: 14px; font-weight: 700; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; box-shadow: 0 6px 12px rgba(245, 158, 11, 0.3);" onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 8px 16px rgba(245, 158, 11, 0.35)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 6px 12px rgba(245, 158, 11, 0.3)'" onclick="respondToReturnRequest(${request.id}, 'request_info')">
                                <i class="fa fa-question"></i> Request Info
                            </button>
                        ` : request.seller_response === 'approved' && (request.request_type === 'return' || request.request_type === 'both') && request.pickup_completed_at && !request.item_received_at ? `
                            <button class="btn btn-cancel-modern" onclick="closeReturnRequestModal()">
                                <i class="fa fa-times"></i> Close
                            </button>
                            <button class="btn btn-save-modern" style="background: #3b82f6;" onclick="confirmItemReceived(${request.id})">
                                <i class="fa fa-check-circle"></i> Confirm Item Received
                            </button>
                        ` : request.status === 'processing' && request.seller_response === 'approved' && !request.refund_processed_at ? `
                            <button class="btn btn-cancel-modern" onclick="closeReturnRequestModal()">
                                <i class="fa fa-times"></i> Close
                            </button>
                            <button class="btn btn-save-modern" style="background: #10b981;" onclick="processRefundFromSeller(${request.id})">
                                <i class="fa fa-money-bill-wave"></i> Process Refund
                            </button>
                        ` : ''}
                    </div>
                ` : `
                    <div class="modal-actions-modern">
                        <button class="btn btn-cancel-modern" onclick="closeReturnRequestModal()">
                            <i class="fa fa-times"></i> Close
                        </button>
                    </div>
                `}
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

async function refreshReturnRequest(requestId) {
    try {
        const response = await authFetch(`/api/sellers/return-refund-requests`);
        if (!response.ok) throw new Error('Failed to refresh request');

        const data = await response.json();
        const requests = data.data?.requests || data.requests || [];
        const request = requests.find(r => r.id === requestId);
        
        if (request) {
            showReturnRequestModal(request);
            notify.success('Request details refreshed');
        } else {
            notify.error('Request not found');
        }
    } catch (error) {
        console.error('Error refreshing request:', error);
        notify.error('Failed to refresh request details');
    }
}

function closeReturnRequestModal() {
    const modal = document.getElementById('returnRequestModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Expose refresh function globally
window.refreshReturnRequest = refreshReturnRequest;

async function respondToReturnRequest(requestId, response) {
    if (response === 'rejected') {
        const reason = prompt('Please provide a reason for rejection:');
        if (!reason || !reason.trim()) {
            notify.error('Rejection reason is required');
            return;
        }
        
        try {
            const res = await authFetch(`/api/sellers/return-refund-requests/${requestId}/respond`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    response: response,
                    rejection_reason: reason.trim()
                })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                notify.success('Request rejected successfully');
                closeReturnRequestModal();
                loadReturnRequests();
            } else {
                notify.error(data.error || 'Failed to respond to request');
            }
        } catch (error) {
            console.error('Error responding to request:', error);
            notify.error('Failed to respond to request');
        }
    } else {
        try {
            const res = await authFetch(`/api/sellers/return-refund-requests/${requestId}/respond`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    response: response
                })
            });

            const data = await res.json();
            if (res.ok && data.success) {
                notify.success(`Request ${response} successfully`);
                closeReturnRequestModal();
                loadReturnRequests();
            } else {
                notify.error(data.error || 'Failed to respond to request');
            }
        } catch (error) {
            console.error('Error responding to request:', error);
            notify.error('Failed to respond to request');
        }
    }
}

async function confirmItemReceived(requestId) {
    if (!confirm('Have you received the returned item? This will initiate the refund process.')) {
        return;
    }

    try {
        const res = await authFetch(`/api/sellers/return-refund-requests/${requestId}/confirm-received`, {
            method: 'POST'
        });

        const data = await res.json();
        if (res.ok && data.success) {
            notify.success('Item receipt confirmed. Refund will be processed.');
            closeReturnRequestModal();
            loadReturnRequests();
        } else {
            notify.error(data.error || 'Failed to confirm item receipt');
        }
    } catch (error) {
        console.error('Error confirming item receipt:', error);
        notify.error('Failed to confirm item receipt');
    }
}

async function processRefundFromSeller(requestId) {
    if (!confirm('Are you sure you want to process this refund? This will notify the admin to complete the refund processing.')) {
        return;
    }
    
    try {
        // Note: Sellers can request refund processing, but only admins can actually process it
        // This will call the admin endpoint
        const response = await authFetch(`/api/admin/return-refund-requests/${requestId}/process-refund`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Failed to process refund. Only admins can process refunds.');
        }
        
        const result = await response.json();
        if (result.success) {
            notify.success(result.message || 'Refund processed successfully!');
            closeReturnRequestModal();
            loadReturnRequests();
        } else {
            throw new Error(result.message || 'Failed to process refund');
        }
    } catch (error) {
        console.error('Error processing refund:', error);
        notify.error('Error processing refund: ' + error.message);
    }
}

// Expose functions globally
window.loadReturnRequests = loadReturnRequests;
window.filterReturnRequests = filterReturnRequests;
window.processRefundFromSeller = processRefundFromSeller;
window.viewReturnRequestDetails = viewReturnRequestDetails;
window.respondToReturnRequest = respondToReturnRequest;
window.confirmItemReceived = confirmItemReceived;
window.closeReturnRequestModal = closeReturnRequestModal;
window.loadReviews = loadReviews;
window.loadProfile = loadProfile;
window.toggleSettingsGroup = toggleSettingsGroup;

// Expose store management functions globally

// Expose product management functions globally
// Note: openProductModal, closeModal, saveProduct, addVariationField, removeVariationField
// are defined directly as window.functionName below
window.editProduct = editProduct;
window.deleteProduct = deleteProduct;
window.filterProducts = filterProducts;
window.viewOrderDetails = viewOrderDetails;
window.updateOrderStatus = updateOrderStatus;
window.printInvoice = printInvoice;
window.filterOrders = filterOrders;
window.filterOrdersByStatus = filterOrdersByStatus;

async function loadDashboardData() {
    try {
        // Clear existing data first to prevent showing stale data
        console.log(`📊 [loadDashboardData] Loading dashboard data`);
        
        // Reset metrics to zero while loading
        if (document.getElementById('totalRevenue')) {
            document.getElementById('totalRevenue').textContent = '₱0.00';
        }
        if (document.getElementById('totalOrders')) {
            document.getElementById('totalOrders').textContent = '0';
        }
        if (document.getElementById('pendingOrders')) {
            document.getElementById('pendingOrders').textContent = '0';
        }
        if (document.getElementById('avgRating')) {
            document.getElementById('avgRating').textContent = '0.0';
        }
        if (document.getElementById('salesToday')) {
            document.getElementById('salesToday').textContent = '₱0.00';
        }
        if (document.getElementById('salesMonth')) {
            document.getElementById('salesMonth').textContent = '₱0.00';
        }
        
        // Clear widgets
        const topProductsTable = document.getElementById('topProductsTable');
        if (topProductsTable) {
            topProductsTable.innerHTML = '<tr><td colspan="2" style="text-align:center;padding:20px;color:#999;">Loading...</td></tr>';
        }
        const activityLog = document.getElementById('activityLog');
        if (activityLog) {
            activityLog.innerHTML = '<p style="text-align:center;padding:20px;color:#999;">Loading...</p>';
        }
        
        // Load main dashboard metrics
        console.log(`🌐 [loadDashboardData] Calling authFetch('/api/sellers/dashboard')...`);
        const response = await authFetch('/api/sellers/dashboard');
        console.log(`📡 [loadDashboardData] Response status: ${response.status} ${response.statusText}`);
        
        if (!response.ok) {
            console.error(`❌ [loadDashboardData] Response not OK: ${response.status}`);
            throw new Error('Failed to load dashboard');
        }
        
        const data = await response.json();
        console.log(`📥 [loadDashboardData] API Response:`, JSON.stringify(data, null, 2));
        
        if (data.success && data.data) {
            const dash = data.data;
            
            console.log(`✅ [loadDashboardData] Dashboard data loaded:`, {
                total_orders: dash.total_orders,
                pending_orders: dash.pending_orders,
                sales_month: dash.sales_month,
                sales_today: dash.sales_today,
                products_count: dash.products_count,
                total_revenue: dash.total_revenue
            });
            
            // Update metric cards (ensure zeros are displayed)
            document.getElementById('totalRevenue').textContent = '₱' + (dash.sales_month || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
            document.getElementById('totalOrders').textContent = dash.total_orders || 0;
            document.getElementById('pendingOrders').textContent = dash.pending_orders || 0;
            document.getElementById('avgRating').textContent = (dash.avg_rating || 0).toFixed(1);
            
            // Update additional metrics if elements exist
            if (document.getElementById('salesToday')) {
                document.getElementById('salesToday').textContent = '₱' + (dash.sales_today || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
            }
            if (document.getElementById('salesMonth')) {
                document.getElementById('salesMonth').textContent = '₱' + (dash.sales_month || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
            }
            
            sellerData = {
                business_name: dash.business_name || 'My Store',
                verified: dash.verified,
                products_count: dash.products_count || 0
            };
            
            if (document.getElementById('sellerName')) {
                document.getElementById('sellerName').textContent = sellerData.business_name;
            }
        }
        
        // Load widgets
        await Promise.all([
            loadTopProducts(),
            loadRecentActivities(),
            loadRevenueTrend(),
            loadOrderGrowth()
        ]);
        
    } catch (err) {
        console.error('❌ [loadDashboardData] Dashboard error:', err);
        notify.error('Failed to load dashboard data');
    }
}

async function loadTopProducts() {
    try {
        console.log(`🛍️ [loadTopProducts] Loading top products`);
        
        const response = await authFetch('/api/sellers/top-products?limit=5');
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.success && data.data) {
            console.log(`✅ [loadTopProducts] Loaded ${data.data.length} products`);
            renderTopProducts(data.data);
        } else {
            // Ensure empty state is shown
            renderTopProducts([]);
        }
    } catch (err) {
        console.error('❌ [loadTopProducts] Error:', err);
        renderTopProducts([]);
    }
}

function renderTopProducts(products) {
    const tbody = document.getElementById('topProductsTable');
    if (!tbody) return;
    
    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center;padding:20px;color:#999;">No sales data yet</td></tr>';
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
            <td style="text-align:right;">
                <strong>${p.total_sold || 0}</strong> sold<br>
                <small style="color:#28a745;">₱${(p.total_revenue || 0).toLocaleString('en-PH', {minimumFractionDigits:2})}</small>
            </td>
        </tr>
    `).join('');
}

async function loadRecentActivities() {
    try {
        console.log(`📋 [loadRecentActivities] Loading activities`);
        
        const response = await authFetch('/api/sellers/recent-activities?limit=10');
        if (!response.ok) {
            console.warn('⚠️ [loadRecentActivities] Response not OK, showing empty state');
            renderRecentActivities([]);
            return;
        }
        
        const data = await response.json();
        console.log(`📥 [loadRecentActivities] API Response:`, data);
        
        if (data.success && data.data) {
            console.log(`✅ [loadRecentActivities] Loaded ${data.data.length} activities:`, data.data);
            renderRecentActivities(data.data);
        } else {
            // Ensure empty state is shown
            console.log(`ℹ️ [loadRecentActivities] No data returned, showing empty state`);
            renderRecentActivities([]);
        }
    } catch (err) {
        console.error('❌ [loadRecentActivities] Error:', err);
        renderRecentActivities([]);
    }
}

function renderRecentActivities(activities) {
    const container = document.getElementById('activityLog');
    if (!container) return;
    
    if (activities.length === 0) {
        container.innerHTML = '<p style="text-align:center;padding:20px;color:#999;">No recent activity</p>';
        return;
    }
    
    container.innerHTML = activities.map(activity => {
        const timeAgo = getTimeAgo(activity.created_at);
        const icon = activity.activity_type === 'order' ? 'fa-cart-shopping' : 'fa-star';
        const statusClass = getStatusClass(activity.status);
        
        return `
            <div class="activity-item">
                <span class="activity-icon"><i class="fa-solid ${icon}"></i></span>
                <div class="activity-details">
                    <p class="activity-text">
                        <strong>${activity.customer_name || 'Customer'}</strong> placed order #${activity.id}
                        <span class="status-badge ${statusClass}">${activity.status}</span>
                    </p>
                    <span class="activity-time">${timeAgo}</span>
                </div>
            </div>
        `;
    }).join('');
}

let revenueTrendChart = null;
async function loadRevenueTrend() {
    try {
        console.log(`📈 [loadRevenueTrend] Loading revenue trend`);
        
        const response = await authFetch('/api/sellers/revenue-trend?period=30');
        if (!response.ok) {
            console.warn('⚠️ [loadRevenueTrend] Response not OK, showing empty chart');
            renderRevenueTrendChart([]);
            return;
        }
        
        const data = await response.json();
        if (data.success && data.data) {
            console.log(`✅ [loadRevenueTrend] Loaded ${data.data.length} data points`);
            renderRevenueTrendChart(data.data || []);
        } else {
            console.log(`ℹ️ [loadRevenueTrend] No data returned, showing empty chart`);
            renderRevenueTrendChart([]);
        }
    } catch (err) {
        console.error('❌ [loadRevenueTrend] Error:', err);
        renderRevenueTrendChart([]);
    }
}

function renderRevenueTrendChart(trendData) {
    const canvas = document.getElementById('revenueTrendChart');
    if (!canvas) return;
    
    // Destroy existing chart
    if (revenueTrendChart) {
        revenueTrendChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    
    // Handle empty data - show empty chart with zero values
    if (!trendData || trendData.length === 0) {
        console.log('ℹ️ [renderRevenueTrendChart] No trend data, showing empty chart');
        trendData = [];
    }
    
    const labels = trendData.length > 0 ? trendData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }) : [];
    const revenues = trendData.length > 0 ? trendData.map(d => d.revenue) : [0];
    
    revenueTrendChart = new Chart(ctx, {
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
                legend: {
                    display: false
                },
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

let orderGrowthChart = null;
async function loadOrderGrowth() {
    try {
        console.log(`📊 [loadOrderGrowth] Loading order growth`);
        
        const response = await authFetch('/api/sellers/order-growth');
        if (!response.ok) {
            console.warn('⚠️ [loadOrderGrowth] Response not OK, showing empty chart');
            renderOrderGrowthChart({ this_month: 0, last_month: 0 });
            return;
        }
        
        const data = await response.json();
        if (data.success && data.data) {
            console.log(`✅ [loadOrderGrowth] Loaded growth data:`, data.data);
            renderOrderGrowthChart(data.data || { this_month: 0, last_month: 0 });
        } else {
            console.log(`ℹ️ [loadOrderGrowth] No data returned, showing empty chart`);
            renderOrderGrowthChart({ this_month: 0, last_month: 0 });
        }
    } catch (err) {
        console.error('❌ [loadOrderGrowth] Error:', err);
        renderOrderGrowthChart({ this_month: 0, last_month: 0 });
    }
}

function renderOrderGrowthChart(growthData) {
    const canvas = document.getElementById('orderGrowthChart');
    if (!canvas) return;
    
    // Destroy existing chart
    if (orderGrowthChart) {
        orderGrowthChart.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    
    orderGrowthChart = new Chart(ctx, {
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
                legend: {
                    display: false
                },
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
                    ticks: {
                        precision: 0
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

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
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

async function loadProducts() {
    try {
        const response = await authFetch('/api/seller/products');
        if (!response.ok) throw new Error('Failed to load products');
        
        const data = await response.json();
        if (data.success) {
            products = data.products || [];
            renderProductsTable();
        }
    } catch (err) {
        console.error('Products error:', err);
    }
}

async function loadOrders(forceRefresh = false) {
    try {
        // Add cache-busting parameter to ensure fresh data
        const url = forceRefresh 
            ? `/api/sellers/orders?_t=${Date.now()}`
            : '/api/sellers/orders';
        
        const response = await authFetch(url);
        if (!response.ok) throw new Error('Failed to load orders');
        
        const data = await response.json();
        if (data.success && data.data) {
            console.log('Loaded orders:', data.data.length, 'orders');
            // Log statuses for debugging
            data.data.forEach(order => {
                console.log(`Order #${order.id}: status = "${order.status}" (type: ${typeof order.status})`);
            });
            renderOrdersTable(data.data);
            // Update badge after loading orders
            if (typeof updateOrdersBadge === 'function') {
                updateOrdersBadge();
            }
        } else {
            console.warn('No orders data in response:', data);
            renderOrdersTable([]);
        }
    } catch (err) {
        console.error('Orders error:', err);
        renderOrdersTable([]);
    }
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById('ordersTableBody');
    if (!tbody) return;
    
    if (!orders || orders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 60px 20px;">
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 16px;">
                        <i class="fa-solid fa-cart-shopping" style="font-size: 64px; color: #ddd;"></i>
                        <h3 style="color: #666; font-weight: 600; margin: 0;">You have no orders yet</h3>
                        <p style="color: #999; margin: 0; max-width: 400px;">When customers purchase your products, their orders will appear here for you to manage.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = orders.map(order => {
        // Normalize status to lowercase for consistency
        const orderStatus = (order.status || 'pending').toLowerCase();
        const statusClass = `status-${orderStatus}`;
        
        // Format status display text
        const statusLabels = {
            'pending': 'Pending',
            'processing': 'Processing',
            'ready': 'Ready for Pickup',
            'dispatched': 'Rider Pick-Up Scheduled',
            'in-transit': 'On the Way',
            'delivered': 'Delivered',
            'completed': 'Completed',
            'cancelled': 'Cancelled'
        };
        const statusDisplay = statusLabels[orderStatus] || orderStatus.charAt(0).toUpperCase() + orderStatus.slice(1);
        
        const orderDate = new Date(order.created_at).toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        
        // Format products list from items
        const productsList = order.items && order.items.length > 0
            ? order.items.map(item => `${item.title} (x${item.quantity})`).join(', ')
            : 'No items';
        
        const total = parseFloat(order.total || 0);
        
        return `
            <tr data-status="${orderStatus}" data-order-id="${order.id}">
                <td>#${order.id}</td>
                <td>
                    <div class="customer-info">
                        <strong>${order.customer_name || 'N/A'}</strong><br>
                        <small>${order.customer_phone || 'No phone'}</small>
                    </div>
                </td>
                <td>${productsList}</td>
                <td>${orderDate}</td>
                <td>₱${total.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
                <td><span class="status-badge ${statusClass}">${statusDisplay}</span></td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-sm btn-sm-primary" onclick="viewOrderDetails(${order.id})" title="View Details" aria-label="View details">
                            <i class="fa-solid fa-eye" aria-hidden="true"></i>
                        </button>
                        <button class="btn-sm btn-sm-secondary" onclick="updateOrderStatus(${order.id})" title="Update Status" aria-label="Update status">
                            <i class="fa-solid fa-pen-to-square" aria-hidden="true"></i>
                        </button>
                        <button class="btn-sm btn-sm-success" onclick="printInvoice(${order.id})" title="Print Invoice" aria-label="Print invoice">
                            <i class="fa-solid fa-print" aria-hidden="true"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function renderProductsTable() {
    const tbody = document.getElementById('productsTableBody');
    if (!tbody) return;
    
    if (products.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    <i class="fa fa-box" style="font-size: 48px; color: #ccc; margin-bottom: 16px;"></i>
                    <p style="color: #666;">No products found. Click "Add New Product" to get started!</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = products.map(p => {
        const stock = p.stock || 0;
        let stockClass = 'normal';
        if (stock === 0) stockClass = 'out';
        else if (stock < 10) stockClass = 'low';
        
        const imgHTML = p.img_url 
            ? `<img src="${p.img_url}" alt="${p.title}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">` 
            : `<div class="product-img"><i class="fa-solid fa-box"></i></div>`;
        
        return `
            <tr>
                <td>P${String(p.id).padStart(3, '0')}</td>
                <td>${imgHTML}</td>
                <td>${p.title || 'N/A'}</td>
                <td>${p.category || 'N/A'}</td>
                <td>₱${(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
                <td><span class="stock-level ${stockClass}">${stock} units</span></td>
                <td><span class="status-badge status-active">Active</span></td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-sm btn-sm-primary" onclick="editProduct(${p.id})" title="Edit">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button class="btn-sm btn-sm-danger" onclick="deleteProduct(${p.id})" title="Delete">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function logout() {
    localStorage.removeItem('hub_access_token');
    localStorage.removeItem('hub_refresh_token');
    window.location.href = 'loginregister.html';
}

// Product Management Functions
async function loadProducts() {
    try {
        const response = await authFetch('/api/sellers/products');
        if (!response.ok) throw new Error('Failed to load products');
        
        const data = await response.json();
        if (data.success && data.data) {
            products = data.data;
            // Debug: Log first product to check image_urls
            if (products.length > 0) {
                console.log('Seller products loaded:', {
                    total: products.length,
                    firstProduct: {
                        id: products[0].id,
                        title: products[0].title,
                        img_url: products[0].img_url,
                        image_urls: products[0].image_urls
                    }
                });
            }
            renderProductsTable();
        } else {
            products = [];
            renderProductsTable();
        }
    } catch (err) {
        console.error('Products error:', err);
        products = [];
        renderProductsTable();
    }
}

function filterProducts() {
    const searchTerm = document.getElementById('productSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#productsTableBody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

// Modal functions moved to bottom of file to avoid duplicates

// Global variable for managing variations
let variationsCount = 0;
let editingProductId = null;

// Make functions globally accessible
window.addVariationField = function() {
    variationsCount++;
    const container = document.getElementById('variationsContainer');
    if (!container) {
        console.error('variationsContainer not found');
        return;
    }
    
    const variationHTML = `
        <div class="variation-item" id="variation-${variationsCount}">
            <div class="form-group">
                <label>Type (e.g., Size, Flavor) <span style="color: red;">*</span></label>
                <input type="text" class="variation-type" placeholder="Size" list="variationTypeList" required />
            </div>
            <div class="form-group">
                <label>Value (e.g., Small, Large) <span style="color: red;">*</span></label>
                <input type="text" class="variation-value" placeholder="Small" required />
            </div>
            <div class="form-group">
                <label>Price Adjustment (₱)</label>
                <input type="number" class="variation-price" placeholder="0.00" step="0.01" value="0" />
            </div>
            <div class="form-group">
                <label>Stock</label>
                <input type="number" class="variation-stock" placeholder="0" min="0" value="0" />
            </div>
            <button type="button" class="btn-remove-variation" onclick="removeVariationField(${variationsCount})" title="Remove">
                <i class="fa fa-times"></i>
            </button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', variationHTML);
    console.log(`Added variation field ${variationsCount}`);
    const item = document.getElementById(`variation-${variationsCount}`);
    if (item) attachVariationRowBehaviors(item);
}

window.removeVariationField = function(id) {
    const item = document.getElementById(`variation-${id}`);
    if (item) {
        item.remove();
        console.log(`Removed variation field ${id}`);
    }
}

// Image preview handler
// Store selected images array
window.selectedProductImages = [];

window.handleProductImageChange = function(event) {
    const files = event.target.files;
    if (!files || files.length === 0) {
        const previewContainer = document.getElementById('imagePreviewContainer');
        if (previewContainer) previewContainer.style.display = 'none';
        window.selectedProductImages = [];
        return;
    }
    
    // Validate and add new files to selected images
    Array.from(files).forEach(file => {
        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            if (window.notify) window.notify.error('Invalid file type. Only JPG, PNG, WEBP, and GIF are allowed.');
            return;
        }
        
        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024; // 5MB in bytes
        if (file.size > maxSize) {
            if (window.notify) window.notify.error('File too large. Maximum size is 5MB.');
            return;
        }
        
        // Check if file already exists (only check files that have a file object)
        const exists = window.selectedProductImages.some(img => 
            img.file && img.file.name === file.name && img.file.size === file.size
        );
        if (!exists) {
            window.selectedProductImages.push({
                file: file,
                preview: URL.createObjectURL(file),
                uploaded: false,
                url: null
            });
        }
    });
    
    // Update file input to reflect selected files
    updateFileInput();
    renderImagePreview();
}

function renderImagePreview() {
    const container = document.getElementById('imagePreviewContainer');
    const grid = document.getElementById('imagePreviewGrid');
    if (!container || !grid) return;
    
    if (window.selectedProductImages.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    grid.innerHTML = '';
    
    window.selectedProductImages.forEach((imgData, index) => {
        const imgDiv = document.createElement('div');
        imgDiv.className = 'image-preview-item';
        imgDiv.style.cssText = 'position: relative; border: 2px solid #ddd; border-radius: 8px; overflow: hidden; aspect-ratio: 1;';
        
        const img = document.createElement('img');
        img.src = imgData.preview;
        img.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
        img.alt = 'Preview';
        
        const controls = document.createElement('div');
        controls.style.cssText = 'position: absolute; top: 5px; right: 5px; display: flex; gap: 5px;';
        
        // Move up button (except first)
        if (index > 0) {
            const moveUp = document.createElement('button');
            moveUp.innerHTML = '<i class="fa fa-arrow-up"></i>';
            moveUp.className = 'btn-icon';
            moveUp.style.cssText = 'background: rgba(0,0,0,0.6); color: white; border: none; border-radius: 4px; padding: 5px 8px; cursor: pointer;';
            moveUp.onclick = () => {
                [window.selectedProductImages[index], window.selectedProductImages[index - 1]] = 
                    [window.selectedProductImages[index - 1], window.selectedProductImages[index]];
                renderImagePreview();
            };
            controls.appendChild(moveUp);
        }
        
        // Move down button (except last)
        if (index < window.selectedProductImages.length - 1) {
            const moveDown = document.createElement('button');
            moveDown.innerHTML = '<i class="fa fa-arrow-down"></i>';
            moveDown.className = 'btn-icon';
            moveDown.style.cssText = 'background: rgba(0,0,0,0.6); color: white; border: none; border-radius: 4px; padding: 5px 8px; cursor: pointer;';
            moveDown.onclick = () => {
                [window.selectedProductImages[index], window.selectedProductImages[index + 1]] = 
                    [window.selectedProductImages[index + 1], window.selectedProductImages[index]];
                renderImagePreview();
            };
            controls.appendChild(moveDown);
        }
        
        // Remove button
        const remove = document.createElement('button');
        remove.innerHTML = '<i class="fa fa-times"></i>';
        remove.className = 'btn-icon';
        remove.style.cssText = 'background: rgba(220,53,69,0.8); color: white; border: none; border-radius: 4px; padding: 5px 8px; cursor: pointer;';
        remove.onclick = () => {
            URL.revokeObjectURL(imgData.preview);
            window.selectedProductImages.splice(index, 1);
            renderImagePreview();
            // Update file input
            updateFileInput();
        };
        controls.appendChild(remove);
        
        imgDiv.appendChild(img);
        imgDiv.appendChild(controls);
        grid.appendChild(imgDiv);
    });
}

function updateFileInput() {
    const input = document.getElementById('productImage');
    if (!input) return;
    
    // Create a new DataTransfer object to update files
    // Only include images that have a file object (new uploads, not existing images)
    const dt = new DataTransfer();
    window.selectedProductImages.forEach(imgData => {
        // Only add files that have a File object (new uploads)
        if (imgData.file && imgData.file instanceof File) {
            dt.items.add(imgData.file);
        }
    });
    input.files = dt.files;
}

// Quick variation type chip setter
window.setVariationType = function(type) {
    const container = document.getElementById('variationsContainer');
    let items = container ? container.querySelectorAll('.variation-item') : [];
    if (!items || items.length === 0) {
        addVariationField();
        items = container.querySelectorAll('.variation-item');
    }
    const last = items[items.length - 1];
    const typeInput = last.querySelector('.variation-type');
    if (typeInput) {
        typeInput.value = type;
        const valueInput = last.querySelector('.variation-value');
        if (valueInput && !valueInput.value) valueInput.focus();
    }
}

// Setup drag-and-drop upload for product image
function initDropzone() {
    const dz = document.getElementById('imageDropzone');
    const input = document.getElementById('productImage');
    if (!dz || !input) return;
    const prevent = e => { e.preventDefault(); e.stopPropagation(); };
    ['dragenter','dragover','dragleave','drop'].forEach(ev => dz.addEventListener(ev, prevent));
    dz.addEventListener('dragover', () => dz.classList.add('dragover'));
    dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
    dz.addEventListener('drop', e => {
        dz.classList.remove('dragover');
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
            // Add files to selected images
            Array.from(files).forEach(file => {
                const exists = window.selectedProductImages.some(img => img.file.name === file.name && img.file.size === file.size);
                if (!exists) {
                    window.selectedProductImages.push({
                        file: file,
                        preview: URL.createObjectURL(file),
                        uploaded: false,
                        url: null
                    });
                }
            });
            updateFileInput();
            renderImagePreview();
        }
    });
}

function renderUploadList(files) {
    const list = document.getElementById('uploadList');
    if (!list) return;
    list.innerHTML = '';
    for (const f of files) {
        const item = document.createElement('div');
        item.className = 'file-item';
        const name = document.createElement('span');
        name.className = 'file-name';
        name.textContent = f.name;
        const progress = document.createElement('div');
        progress.className = 'file-progress';
        const bar = document.createElement('span');
        progress.appendChild(bar);
        item.appendChild(name);
        item.appendChild(progress);
        list.appendChild(item);
    }
    list.style.display = files.length ? 'block' : 'none';
}

function clearProductForm() {
    // Clear selected images
    window.selectedProductImages.forEach(img => {
        if (img.preview && img.preview.startsWith('blob:')) {
            URL.revokeObjectURL(img.preview);
        }
    });
    window.selectedProductImages = [];
    const previewContainer = document.getElementById('imagePreviewContainer');
    if (previewContainer) previewContainer.style.display = 'none';
    const imageInput = document.getElementById('productImage');
    if (imageInput) imageInput.value = '';
    document.getElementById('productName').value = '';
    document.getElementById('productCategory').value = '';
    document.getElementById('productPrice').value = '';
    document.getElementById('productStock').value = '';
    document.getElementById('productImage').value = '';
    document.getElementById('productDescription').value = '';
    document.getElementById('manufactureDate').value = '';
    document.getElementById('expiryDate').value = '';
    
    // Clear image preview
    const previewDiv = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    if (previewDiv) previewDiv.style.display = 'none';
    if (previewImg) previewImg.src = '';
    
    // Clear all error messages
    document.querySelectorAll('.error-message').forEach(el => el.classList.remove('show'));
    
    // Clear variations
    document.getElementById('variationsContainer').innerHTML = '';
    variationsCount = 0;
    editingProductId = null;
}

function validateProductForm() {
    let isValid = true;
    
    // Clear previous errors
    document.querySelectorAll('.error-message').forEach(el => el.classList.remove('show'));
    
    const name = document.getElementById('productName').value.trim();
    const category = document.getElementById('productCategory').value;
    const price = parseFloat(document.getElementById('productPrice').value);
    const stock = parseInt(document.getElementById('productStock').value);
    const imageInput = document.getElementById('productImage');
    const description = document.getElementById('productDescription').value.trim();
    
    if (!name) {
        showError('productNameError', 'Product name is required');
        isValid = false;
    }
    
    if (!category) {
        showError('productCategoryError', 'Please select a category');
        isValid = false;
    }
    
    if (!price || price <= 0) {
        showError('productPriceError', 'Price must be greater than 0');
        isValid = false;
    }
    
    if (isNaN(stock) || stock < 0) {
        showError('productStockError', 'Stock must be 0 or greater');
        isValid = false;
    }
    
    // Only validate image if creating new product (not editing)
    if (!editingProductId && (!window.selectedProductImages || window.selectedProductImages.length === 0)) {
        showError('productImageError', 'Please select at least one product image');
        isValid = false;
    }
    
    if (!description) {
        showError('productDescriptionError', 'Product description is required');
        isValid = false;
    }
    
    return isValid;
}

function showError(elementId, message) {
    const errorEl = document.getElementById(elementId);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('show');
    }
}

window.saveProduct = async function() {
    console.log('saveProduct called');
    if (!validateProductForm()) {
        notify.error('Please fix the errors in the form');
        return;
    }
    
    const saveBtn = document.getElementById('saveProductBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Saving...';
    
    try {
        // Upload images first (if files are selected)
        let imageUrls = [];
        
        // Check if user selected new image files
        if (window.selectedProductImages && window.selectedProductImages.length > 0) {
            const newImages = window.selectedProductImages.filter(img => !img.uploaded);
            const existingImages = window.selectedProductImages.filter(img => img.uploaded && img.url);
            
            // Collect existing image URLs first
            if (existingImages.length > 0) {
                imageUrls = existingImages.map(img => img.url).filter(url => url);
                console.log('Found existing images:', imageUrls);
            }
            
            if (newImages.length > 0) {
                notify.info(`Uploading ${newImages.length} image(s)...`);
                
                // Upload all new images
                for (const imgData of newImages) {
            const formData = new FormData();
                    formData.append('image', imgData.file);
            
            const uploadResponse = await authFetch('/api/upload/product-image', {
                method: 'POST',
                body: formData
            });
            
            if (!uploadResponse.ok) {
                const error = await uploadResponse.json();
                throw new Error(error.error || 'Failed to upload image');
            }
            
            const uploadResult = await uploadResponse.json();
            if (!uploadResult.success) {
                throw new Error(uploadResult.error || 'Image upload failed');
            }
            
                    imgData.uploaded = true;
                    imgData.url = uploadResult.data.path;
                    // Add new image URL to the array (combine with existing)
                    imageUrls.push(uploadResult.data.path);
                }
                
                notify.success(`${newImages.length} image(s) uploaded successfully`);
            }
            
            // If we have any images (existing or new), use them
            if (imageUrls.length > 0) {
                console.log('Final image URLs to send (existing + new):', imageUrls);
            }
        } else if (!editingProductId) {
            // Only require image for new products
            throw new Error('Please select at least one product image');
        } else {
            // When editing, if no images selected at all, don't send image_urls to avoid clearing
            console.log('Editing product - no images in selectedProductImages, keeping existing images in database');
        }
        
        // Collect product data
        const productData = {
            title: document.getElementById('productName').value.trim(),
            category: document.getElementById('productCategory').value,
            price: parseFloat(document.getElementById('productPrice').value),
            stock: parseInt(document.getElementById('productStock').value),
            description: document.getElementById('productDescription').value.trim(),
            manufacture_date: document.getElementById('manufactureDate').value || null,
            expiry_date: document.getElementById('expiryDate').value || null
        };
        // No store_id - single store per seller
        
        // Add image_urls array - always send if we have images (for editing, this ensures images are updated)
        if (imageUrls.length > 0) {
            productData.image_urls = imageUrls;
            // Keep img_url for backward compatibility (first image)
            productData.img_url = imageUrls[0];
            console.log('Sending product data with images:', {
                image_urls: imageUrls,
                img_url: imageUrls[0],
                total_images: imageUrls.length,
                is_editing: !!editingProductId
            });
        } else if (editingProductId && window.selectedProductImages && window.selectedProductImages.length > 0) {
            // If editing and we have images in selectedProductImages but no URLs, something went wrong
            console.error('Editing product but no image URLs collected!', {
                selectedProductImages: window.selectedProductImages,
                editingProductId: editingProductId
            });
        } else if (!editingProductId) {
            console.warn('No image URLs to send for new product');
        }
        
        let response, productId;
        
        if (editingProductId) {
            // Update existing product
            response = await authFetch(`/api/sellers/products/${editingProductId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(productData)
            });
            productId = editingProductId;
        } else {
            // Create new product
            response = await authFetch('/api/sellers/products', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(productData)
            });
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create product');
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to save product');
        }
        
        if (!editingProductId) {
            productId = result.data.product_id;
        }
        
        console.log('Product saved, productId:', productId);
        
        // If editing, delete all existing variations first to avoid duplicates
        if (editingProductId) {
            try {
                // Fetch existing variations
                const existingVarsResponse = await authFetch(`/api/sellers/products/${productId}/variations`);
                if (existingVarsResponse.ok) {
                    const existingVarsData = await existingVarsResponse.json();
                    if (existingVarsData.success && existingVarsData.data && existingVarsData.data.length > 0) {
                        console.log(`Deleting ${existingVarsData.data.length} existing variations before updating...`);
                        // Delete each existing variation
                        for (const existingVar of existingVarsData.data) {
                            const deleteResponse = await authFetch(`/api/sellers/products/${productId}/variations/${existingVar.id}`, {
                                method: 'DELETE'
                            });
                            if (!deleteResponse.ok) {
                                console.warn(`Failed to delete variation ${existingVar.id}, continuing...`);
                            }
                        }
                        console.log('Existing variations deleted successfully');
                    }
                }
            } catch (error) {
                console.warn('Error deleting existing variations:', error);
                // Continue anyway - we'll try to add new ones
            }
        }
        
        // Collect variations from form
        const variations = [];
        const variationItems = document.querySelectorAll('.variation-item');
        console.log('Found variation items:', variationItems.length);
        variationItems.forEach(item => {
            const type = item.querySelector('.variation-type').value.trim();
            const value = item.querySelector('.variation-value').value.trim();
            const priceAdj = parseFloat(item.querySelector('.variation-price').value) || 0;
            const stock = parseInt(item.querySelector('.variation-stock').value) || 0;
            
            console.log('Processing variation:', { type, value, priceAdj, stock });
            
            if (type && value) {
                variations.push({
                    variation_type: type,
                    variation_value: value,
                    price_adjustment: priceAdj,
                    stock: stock
                });
            } else {
                console.warn('Skipping variation - missing type or value:', { type, value });
            }
        });
        
        // Add variations if any
        if (variations.length > 0) {
            console.log(`Saving ${variations.length} variations for product ${productId}:`, variations);
            let savedCount = 0;
            for (const variation of variations) {
                const varResponse = await authFetch(`/api/sellers/products/${productId}/variations`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(variation)
                });
                
                if (!varResponse.ok) {
                    const error = await varResponse.json();
                    console.error('Failed to save variation:', variation, error);
                    throw new Error(`Failed to save variation "${variation.variation_type}: ${variation.variation_value}": ${error.error || 'Unknown error'}`);
                }
                
                const varResult = await varResponse.json();
                if (!varResult.success) {
                    console.error('Variation save unsuccessful:', variation, varResult);
                    throw new Error(`Failed to save variation "${variation.variation_type}: ${variation.variation_value}": ${varResult.error || 'Unknown error'}`);
                }
                
                savedCount++;
                console.log(`Variation ${savedCount}/${variations.length} saved successfully:`, varResult);
            }
            notify.success(`Product saved with ${savedCount} variation(s)!`);
        } else {
            // If editing and no variations, all variations were removed
            if (editingProductId) {
                notify.success('Product updated successfully! All variations removed.');
            } else {
                notify.success(result.message || 'Product created successfully! It will appear on shop.html immediately.');
            }
        }
        
        closeModal('productModal');
        clearProductForm();
        
        // Reload products
        await loadProducts();
        
    } catch (error) {
        console.error('Save product error:', error);
        notify.error(error.message || 'Failed to save product')
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fa fa-save"></i> Save Product';
    }
}

window.openProductModal = function(mode, productId = null) {
    const modal = document.getElementById('productModal');
    const title = document.getElementById('productModalTitle');
    const imageHelpText = document.getElementById('imageHelpText');
    const imageRequiredIndicator = document.getElementById('imageRequiredIndicator');
    
    clearProductForm();
    
    if (mode === 'add') {
        title.textContent = 'Add New Product';
        editingProductId = null;
        if (imageHelpText) {
            imageHelpText.textContent = 'Upload a product image (JPG, PNG, WEBP - Max 5MB)';
        }
        if (imageRequiredIndicator) {
            imageRequiredIndicator.style.display = 'inline';
        }
    } else if (mode === 'edit' && productId) {
        title.textContent = 'Edit Product';
        editingProductId = productId;
        if (imageHelpText) {
            imageHelpText.textContent = 'Upload a new image to replace the current one (Optional - JPG, PNG, WEBP - Max 5MB)';
        }
        if (imageRequiredIndicator) {
            imageRequiredIndicator.style.display = 'none';
        }
        // Load product data would go here
        loadProductForEdit(productId);
    }
    
    modal.style.display = 'block';
    if (document && document.body) {
        document.body.classList.add('modal-open');
    }
    // UX: focus first field and scroll to top
    const nameInput = document.getElementById('productName');
    if (nameInput) {
        setTimeout(() => nameInput.focus(), 50);
    }
    const body = document.querySelector('#productModal .modal-body-modern');
    if (body) body.scrollTop = 0;
    // Initialize dropzone for image upload
    initDropzone();
}

window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        if (document && document.body) {
            document.body.classList.remove('modal-open');
        }
    }
}

async function editProduct(productId) {
    openProductModal('edit', productId);
}

async function loadProductForEdit(productId) {
    try {
        // Find product in current products array
        let product = products.find(p => p.id === productId);
        if (!product) {
            notify.error('Product not found');
            return;
        }
        
        // Load existing images (from image_urls or img_url)
        // First try to fetch fresh product data with images using the public endpoint
        try {
            const freshProductResponse = await fetch(`http://127.0.0.1:5000/api/products/${productId}`);
            if (freshProductResponse.ok) {
                const freshProduct = await freshProductResponse.json();
                if (freshProduct && freshProduct.id) {
                    product = freshProduct; // Use fresh data with image_urls
                    console.log('Loaded fresh product data with images:', {
                        image_urls: product.image_urls,
                        img_url: product.img_url
                    });
                }
            }
        } catch (error) {
            console.warn('Could not fetch fresh product data, using cached:', error);
        }
        
        // Populate form
        document.getElementById('productName').value = product.title || '';
        document.getElementById('productCategory').value = product.category || '';
        document.getElementById('productPrice').value = product.price || '';
        document.getElementById('productStock').value = product.stock || '';
        document.getElementById('productDescription').value = product.description || '';
        document.getElementById('manufactureDate').value = product.manufacture_date || '';
        document.getElementById('expiryDate').value = product.expiry_date || '';
        
        // Clear and reset image selection
        const imageInput = document.getElementById('productImage');
        imageInput.value = ''; // Clear file input
        window.selectedProductImages = [];
        
        const existingImages = (product.image_urls && Array.isArray(product.image_urls) && product.image_urls.length > 0)
            ? product.image_urls 
            : (product.img_url ? [product.img_url] : []);
        
        console.log('Loading existing images for edit:', existingImages);
        
        if (existingImages.length > 0) {
            existingImages.forEach((imgUrl, index) => {
                // Ensure URL is properly formatted
                let imageUrl = imgUrl;
                if (imageUrl && !imageUrl.startsWith('http')) {
                    imageUrl = imageUrl.startsWith('/') ? imageUrl : `/${imageUrl}`;
                }
                
                window.selectedProductImages.push({
                    file: null, // No file object for existing images
                    preview: imageUrl.startsWith('http') ? imageUrl : `http://127.0.0.1:5000${imageUrl}`,
                    uploaded: true,
                    url: imageUrl.startsWith('/') ? imageUrl : `/${imageUrl.replace(/^\/+/, '')}`
                });
            });
            renderImagePreview();
        } else {
            console.warn('No existing images found for product:', productId);
        }
        
        // Load variations if they exist
        const varResponse = await authFetch(`/api/sellers/products/${productId}/variations`);
        if (varResponse.ok) {
            const varData = await varResponse.json();
            if (varData.success && varData.data && varData.data.length > 0) {
                // Clear existing variations
                document.getElementById('variationsContainer').innerHTML = '';
                variationsCount = 0;
                
                // Add each variation
                varData.data.forEach(variation => {
                    variationsCount++;
                    const container = document.getElementById('variationsContainer');
                    const variationHTML = `
                        <div class="variation-item" id="variation-${variationsCount}" data-variation-id="${variation.id}">
                            <div class="form-group">
                                <label>Type (e.g., Size, Flavor)</label>
                                <input type="text" class="variation-type" value="${variation.variation_type}" placeholder="Size" list="variationTypeList" />
                            </div>
                            <div class="form-group">
                                <label>Value (e.g., Small, Large)</label>
                                <input type="text" class="variation-value" value="${variation.variation_value}" placeholder="Small" />
                            </div>
                            <div class="form-group">
                                <label>Price Adjustment (₱)</label>
                                <input type="number" class="variation-price" value="${variation.price_adjustment || 0}" placeholder="0.00" step="0.01" />
                            </div>
                            <div class="form-group">
                                <label>Stock</label>
                                <input type="number" class="variation-stock" value="${variation.stock || 0}" placeholder="0" min="0" />
                            </div>
                            <button type="button" class="btn-remove-variation" onclick="removeVariationField(${variationsCount})" title="Remove">
                                <i class="fa fa-times"></i>
                            </button>
                        </div>
                    `;
                    container.insertAdjacentHTML('beforeend', variationHTML);
                    const item = document.getElementById(`variation-${variationsCount}`);
                    if (item) attachVariationRowBehaviors(item);
                });
            }
        }
    } catch (error) {
        console.error('Load product error:', error);
        notify.error('Failed to load product details');
    }
}

// Attach behaviors to a variation row: dynamic value presets and inline validation
function attachVariationRowBehaviors(item) {
    const typeInput = item.querySelector('.variation-type');
    const valueInput = item.querySelector('.variation-value');
    if (!typeInput || !valueInput) return;
    const update = () => updateValueDatalist(item);
    typeInput.addEventListener('input', update);
    valueInput.addEventListener('focus', update);
    // Minimal inline validation styles
    [typeInput, valueInput].forEach(input => {
        input.addEventListener('blur', () => {
            if (!input.value.trim()) {
                input.classList.add('input-invalid');
            } else {
                input.classList.remove('input-invalid');
            }
        });
        input.addEventListener('input', () => {
            if (input.value.trim()) input.classList.remove('input-invalid');
        });
    });
    // Initialize datalist based on current type
    update();
}

function updateValueDatalist(item) {
    const type = item.querySelector('.variation-type')?.value?.trim().toLowerCase();
    const valueInput = item.querySelector('.variation-value');
    if (!valueInput) return;
    let listId = '';
    if (type === 'size') listId = 'sizeValueList';
    else if (type === 'flavor') listId = 'flavorValueList';
    else if (type === 'color') listId = 'colorValueList';
    else listId = '';
    if (listId) {
        valueInput.setAttribute('list', listId);
    } else {
        valueInput.removeAttribute('list');
    }
}

// Expose helpers if needed
window.attachVariationRowBehaviors = attachVariationRowBehaviors;
window.updateValueDatalist = updateValueDatalist;

async function deleteProduct(productId) {
    if (!confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await authFetch(`/api/sellers/products/${productId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete product');
        }
        
        const result = await response.json();
        
        if (result.success) {
            notify.success('Product deleted successfully');
            await loadProducts();
        } else {
            throw new Error(result.error || 'Failed to delete product');
        }
    } catch (error) {
        console.error('Delete product error:', error);
        notify.error(error.message || 'Failed to delete product');
    }
}

async function updateProduct(productId) {
    try {
        const response = await authFetch(`/api/products/${productId}`);
        const data = await response.json();
        
        if (data.success && data.product) {
            const product = data.product;
            document.getElementById('productName').value = product.title || '';
            document.getElementById('productCategory').value = product.category || '';
            document.getElementById('productPrice').value = product.price || '';
            document.getElementById('productStock').value = product.stock || '';
            document.getElementById('productImage').value = product.img_url || '';
            document.getElementById('productDescription').value = product.description || '';
        }
    } catch (error) {
        console.error('Load product error:', error);
    }
}

function editProduct(productId) {
    openProductModal('edit', productId);
}

async function deleteProduct(productId) {
    if (!confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await authFetch(`/api/sellers/products/${productId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete product');
        }
        
        const result = await response.json();
        
        if (window.notify) {
            window.notify.success(result.message || 'Product deleted successfully');
        }
        
        // Reload products
        await loadProducts();
        
    } catch (error) {
        console.error('Delete product error:', error);
        if (window.notify) {
            window.notify.error(error.message || 'Failed to delete product');
        } else {
            alert('Error: ' + error.message);
        }
    }
}

function toggleProductStatus(productId) {
    // Implement toggle status logic here
    alert('Product status toggled: ' + productId);
    // Refresh product list
    // loadProducts();
}

// Order Management Functions
function filterOrders() {
    const searchTerm = document.getElementById('orderSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#ordersTableBody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

function filterOrdersByStatus(status) {
    const rows = document.querySelectorAll('#ordersTableBody tr');
    const buttons = document.querySelectorAll('.filter-buttons .filter-btn');
    
    // Update active button
    buttons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Filter rows
    rows.forEach(row => {
        if (status === 'all') {
            row.style.display = '';
        } else {
            const rowStatus = row.getAttribute('data-status');
            row.style.display = rowStatus === status ? '' : 'none';
        }
    });
}

// Store current order data for print function
let currentOrderData = null;

async function viewOrderDetails(orderId) {
    const modal = document.getElementById('orderModal');
    
    try {
        // Load actual order data from backend
        const response = await authFetch(`/api/sellers/orders/${orderId}`);
        if (!response.ok) throw new Error('Failed to load order');
        
        const data = await response.json();
        if (data.success && data.data) {
            const order = data.data;
            
            // Store order data for print function
            currentOrderData = { ...order, id: orderId };
            
            // Format order date
            const orderDate = order.created_at ? new Date(order.created_at).toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }) : 'N/A';
            
            // Update order information
            document.getElementById('detailOrderId').textContent = '#' + orderId;
            document.getElementById('detailOrderDate').textContent = orderDate;
            document.getElementById('detailOrderStatus').innerHTML = `<span class="status-badge status-${(order.status || 'pending').toLowerCase()}">${(order.status || 'Pending').charAt(0).toUpperCase() + (order.status || 'pending').slice(1)}</span>`;
            document.getElementById('detailOrderAmount').textContent = '₱' + (parseFloat(order.total || 0)).toLocaleString('en-PH', { minimumFractionDigits: 2 });
            
            // Update customer details
            document.getElementById('detailCustomerName').textContent = order.customer_name || 'N/A';
            document.getElementById('detailCustomerEmail').textContent = order.customer_email || 'N/A';
            document.getElementById('detailCustomerPhone').textContent = order.customer_phone || 'N/A';
            
            // Update shipping information
            const address = order.customer_address || order.shipping_address || 'N/A';
            document.getElementById('detailShippingAddress').textContent = address;
            document.getElementById('detailShippingCity').textContent = order.shipping_city || order.city || 'N/A';
            document.getElementById('detailShippingPostal').textContent = order.shipping_postal || order.postal_code || 'N/A';
            
            // Update payment method
            const paymentMethodEl = document.getElementById('detailPaymentMethod');
            if (paymentMethodEl) {
                paymentMethodEl.textContent = order.payment || 'Cash on Delivery';
            }
            
            // Update products list
            const productListContainer = document.getElementById('detailProductList');
            if (order.items && order.items.length > 0) {
                productListContainer.innerHTML = order.items.map(item => {
                    const itemPrice = parseFloat(item.price || 0);
                    const itemQuantity = parseInt(item.quantity || 1);
                    const itemTotal = itemPrice * itemQuantity;
                    const variationInfo = item.variation_details ? 
                        JSON.parse(item.variation_details).variation_value || '' : '';
                    return `
                        <div class="product-item">
                            <div>
                                <strong>${item.title || 'Product'}</strong>
                                ${variationInfo ? `<small>${variationInfo}</small>` : ''}
                            </div>
                            <div>
                                <div class="product-qty">Qty: ${itemQuantity}</div>
                                <div class="product-price">₱${itemPrice.toLocaleString('en-PH', { minimumFractionDigits: 2 })} each</div>
                                <div class="product-total">₱${itemTotal.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                productListContainer.innerHTML = '<div class="product-item"><div>No items found</div></div>';
            }
        }
    } catch (err) {
        console.error('Order details error:', err);
        if (typeof notify !== 'undefined') {
            notify.error('Failed to load order details. Please try again.');
        } else {
        alert('Failed to load order details');
        }
        return;
    }
    
    modal.style.display = 'block';
}

function updateOrderStatus(orderId) {
    const modal = document.getElementById('updateStatusModal');
    // Store order ID for saving
    modal.dataset.orderId = orderId;
    document.getElementById('statusOrderId').value = '#' + orderId;
    
    // Load current status from the specific row for this order
    const currentRow = document.querySelector(`tr[data-order-id="${orderId}"]`) || 
                       document.querySelector(`tr:has(td:first-child:contains("#${orderId}"))`);
    
    // Try to find row by checking the first cell content
    let currentStatus = 'pending';
    const allRows = document.querySelectorAll('#ordersTableBody tr[data-status]');
    for (const row of allRows) {
        const firstCell = row.querySelector('td:first-child');
        if (firstCell && firstCell.textContent.trim() === `#${orderId}`) {
            currentStatus = row.getAttribute('data-status') || 'pending';
            break;
        }
    }
    
    const statusSelect = document.getElementById('newOrderStatus');
    if (statusSelect) {
        statusSelect.value = currentStatus;
    }
    
    // Clear notes
    document.getElementById('statusNotes').value = '';
    
    modal.style.display = 'block';
}

async function saveOrderStatus() {
    const modal = document.getElementById('updateStatusModal');
    const orderId = modal.dataset.orderId;
    const newStatus = document.getElementById('newOrderStatus').value;
    const notes = document.getElementById('statusNotes').value;
    
    if (!orderId) {
        if (typeof notify !== 'undefined') {
            notify.error('Order ID is missing');
        } else {
            alert('Order ID is missing');
        }
        return;
    }
    
    if (!newStatus) {
        if (typeof notify !== 'undefined') {
            notify.error('Please select a status');
        } else {
        alert('Please select a status');
        }
        return;
    }
    
    try {
        // Update order status via API
        const response = await authFetch(`/api/orders/${orderId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: newStatus,
                notes: notes || null
            })
        });
        
        const data = await response.json();
        
        console.log('Status update response:', data);
        
        if (response.ok && data.success) {
            // Use the status from the response if available, otherwise use the one we sent
            const actualStatus = (data.new_status || newStatus).toLowerCase();
            console.log(`Order #${orderId} status successfully updated to: ${actualStatus}`);
            
            if (typeof notify !== 'undefined') {
                notify.success(`Order #${orderId} status updated to ${actualStatus}`);
            } else {
                alert(`Order #${orderId} status updated to ${actualStatus}`);
            }
            
    closeModal('updateStatusModal');
    
            // Immediately update the row in the table for instant feedback
            const orderRow = document.querySelector(`tr[data-order-id="${orderId}"]`);
            if (orderRow) {
                // Update the data-status attribute
                orderRow.setAttribute('data-status', actualStatus);
                
                // Update the status badge
                const statusCell = orderRow.querySelector('td:nth-child(6)'); // Status is 6th column
                if (statusCell) {
                    const statusLabels = {
                        'pending': 'Pending',
                        'processing': 'Processing',
                        'ready': 'Ready for Pickup',
                        'dispatched': 'Rider Pick-Up Scheduled',
                        'in-transit': 'On the Way',
                        'delivered': 'Delivered',
                        'completed': 'Completed',
                        'cancelled': 'Cancelled'
                    };
                    const statusDisplay = statusLabels[actualStatus] || actualStatus.charAt(0).toUpperCase() + actualStatus.slice(1);
                    const statusClass = `status-${actualStatus}`;
                    statusCell.innerHTML = `<span class="status-badge ${statusClass}">${statusDisplay}</span>`;
                    console.log(`Updated status display in table for order #${orderId} to: ${statusDisplay}`);
                } else {
                    console.warn(`Could not find status cell for order #${orderId}`);
                }
            } else {
                console.warn(`Could not find order row for order #${orderId}`);
            }
            
            // Refresh orders list to ensure we have the latest data from backend
            // Add a small delay to ensure backend has committed the change
            // Use forceRefresh to bypass any caching
            setTimeout(() => {
                console.log('Refreshing orders list from server with force refresh...');
                loadOrders(true); // Force refresh with cache-busting
            }, 500);
        } else {
            console.error('Status update failed:', data);
            throw new Error(data.error || 'Failed to update order status');
        }
    } catch (err) {
        console.error('Update order status error:', err);
        if (typeof notify !== 'undefined') {
            notify.error('Failed to update order status. Please try again.');
        } else {
            alert('Failed to update order status. Please try again.');
        }
    }
}

async function printInvoice(orderId) {
    // If orderId is not provided, use current order data from modal
    let order = null;
    
    if (orderId && currentOrderData && currentOrderData.id == orderId) {
        order = currentOrderData;
    } else if (orderId) {
        // Fetch order data if not already loaded
        try {
            const response = await authFetch(`/api/sellers/orders/${orderId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    order = { ...data.data, id: orderId };
                }
            }
        } catch (err) {
            console.error('Error fetching order for print:', err);
        }
    } else if (currentOrderData) {
        order = currentOrderData;
    }
    
    if (!order) {
        if (typeof notify !== 'undefined') {
            notify.error('Order data not available. Please view order details first.');
        } else {
            alert('Order data not available. Please view order details first.');
        }
        return;
    }
    
    // Format order date
    const orderDate = order.created_at ? new Date(order.created_at).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }) : 'N/A';
    
    // Format address
    const address = order.customer_address || order.shipping_address || 'N/A';
    const city = order.shipping_city || order.city || '';
    const postal = order.shipping_postal || order.postal_code || '';
    const fullAddress = [address, city, postal].filter(Boolean).join(', ') || 'N/A';
    
    // Calculate totals
    const subtotal = parseFloat(order.subtotal || order.total || 0);
    const deliveryFee = parseFloat(order.delivery_fee || 0);
    const total = parseFloat(order.total || subtotal + deliveryFee);
    
    // Build products table rows
    let productsRows = '';
    if (order.items && order.items.length > 0) {
        productsRows = order.items.map(item => {
            const itemPrice = parseFloat(item.price || 0);
            const itemQuantity = parseInt(item.quantity || 1);
            const itemTotal = itemPrice * itemQuantity;
            const variationInfo = item.variation_details ? 
                ` (${JSON.parse(item.variation_details).variation_value || ''})` : '';
            return `
                <tr>
                    <td>${item.title || 'Product'}${variationInfo}</td>
                    <td style="text-align: center;">${itemQuantity}</td>
                    <td style="text-align: right;">₱${itemPrice.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
                    <td style="text-align: right;">₱${itemTotal.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</td>
                </tr>
            `;
        }).join('');
    } else {
        productsRows = '<tr><td colspan="4" style="text-align: center;">No items</td></tr>';
    }
    
    // Create a printable invoice
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
        <head>
            <title>Invoice - Order #${order.id || orderId || 'Order'}</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: Arial, sans-serif; 
                    padding: 40px; 
                    color: #333;
                    background: white;
                }
                .invoice-header { 
                    text-align: center; 
                    margin-bottom: 40px;
                    border-bottom: 3px solid #333;
                    padding-bottom: 20px;
                }
                .invoice-header h1 {
                    font-size: 32px;
                    margin-bottom: 10px;
                    color: #333;
                }
                .invoice-details { 
                    margin: 30px 0;
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 30px;
                }
                .detail-section {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                }
                .detail-section h3 {
                    margin-bottom: 15px;
                    color: #333;
                    border-bottom: 2px solid #333;
                    padding-bottom: 8px;
                }
                .detail-row {
                    margin: 10px 0;
                    display: flex;
                    justify-content: space-between;
                }
                .detail-row strong {
                    color: #666;
                }
                .invoice-table { 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 30px 0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .invoice-table th, .invoice-table td { 
                    border: 1px solid #ddd; 
                    padding: 12px; 
                    text-align: left; 
                }
                .invoice-table th { 
                    background: #333;
                    color: white;
                    font-weight: bold;
                }
                .invoice-table tr:nth-child(even) {
                    background: #f8f9fa;
                }
                .totals-section {
                    margin-top: 30px;
                    text-align: right;
                }
                .total-row {
                    display: flex;
                    justify-content: flex-end;
                    margin: 8px 0;
                    padding: 8px 0;
                }
                .total-row label {
                    width: 200px;
                    text-align: right;
                    margin-right: 20px;
                    font-weight: 600;
                }
                .total-row span {
                    width: 150px;
                    text-align: right;
                }
                .total-final {
                    font-size: 20px;
                    font-weight: bold;
                    border-top: 2px solid #333;
                    padding-top: 10px;
                    margin-top: 10px;
                }
                .footer {
                    margin-top: 50px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    border-top: 1px solid #ddd;
                    padding-top: 20px;
                }
                @media print { 
                    button { display: none; }
                    body { padding: 20px; }
                }
                @page {
                    margin: 1cm;
                }
            </style>
        </head>
        <body>
            <div class="invoice-header">
                <h1>INVOICE</h1>
                <p style="font-size: 18px; font-weight: bold;">Order ID: #${order.id || orderId || 'N/A'}</p>
            </div>
            <div class="invoice-details">
                <div class="detail-section">
                    <h3>Order Information</h3>
                    <div class="detail-row">
                        <strong>Order Date:</strong>
                        <span>${orderDate}</span>
                    </div>
                    <div class="detail-row">
                        <strong>Status:</strong>
                        <span>${(order.status || 'Pending').charAt(0).toUpperCase() + (order.status || 'pending').slice(1)}</span>
                    </div>
                    <div class="detail-row">
                        <strong>Payment Method:</strong>
                        <span>${order.payment || 'Cash on Delivery'}</span>
                    </div>
                </div>
                <div class="detail-section">
                    <h3>Customer Information</h3>
                    <div class="detail-row">
                        <strong>Name:</strong>
                        <span>${order.customer_name || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <strong>Email:</strong>
                        <span>${order.customer_email || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <strong>Phone:</strong>
                        <span>${order.customer_phone || 'N/A'}</span>
                    </div>
                    <div class="detail-row">
                        <strong>Address:</strong>
                        <span>${fullAddress}</span>
                    </div>
                </div>
            </div>
            <table class="invoice-table">
                <thead>
                    <tr>
                        <th>Product Name</th>
                        <th style="text-align: center;">Quantity</th>
                        <th style="text-align: right;">Price per Item</th>
                        <th style="text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${productsRows}
                </tbody>
            </table>
            <div class="totals-section">
                <div class="total-row">
                    <label>Subtotal:</label>
                    <span>₱${subtotal.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</span>
            </div>
                ${deliveryFee > 0 ? `
                <div class="total-row">
                    <label>Delivery Fee:</label>
                    <span>₱${deliveryFee.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</span>
                </div>
                ` : ''}
                <div class="total-row total-final">
                    <label>Total Amount:</label>
                    <span>₱${total.toLocaleString('en-PH', { minimumFractionDigits: 2 })}</span>
                </div>
            </div>
            <div class="footer">
                <p>Thank you for your business!</p>
                <p>This is a computer-generated invoice.</p>
            </div>
            <div style="text-align: center; margin-top: 30px;">
                <button onclick="window.print()" style="padding: 12px 24px; background: #333; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">Print Invoice</button>
            </div>
        </body>
        </html>
    `);
    printWindow.document.close();
    // Auto-print after a short delay to ensure content is loaded
    setTimeout(() => {
        printWindow.print();
    }, 250);
}

function editProfile() {
    // Open edit profile modal
    const modal = document.getElementById('editProfileModal');
    if (!modal) {
        // Create modal if it doesn't exist
        createEditProfileModal();
    } else {
        // Load current data into modal
        loadProfileDataIntoEditModal();
        modal.style.display = 'block';
    }
}

function createEditProfileModal() {
    const modalHTML = `
        <div id="editProfileModal" class="modal" style="display: block;">
            <div class="modal-content modal-large modern-modal">
                <div class="modal-header-modern">
                    <div class="modal-header-content">
                        <i class="fa-solid fa-user-edit" aria-hidden="true" style="font-size: 24px;"></i>
                        <h2>Edit Profile</h2>
                    </div>
                    <button class="modal-close-modern" onclick="closeEditProfileModal()" aria-label="Close">&times;</button>
                </div>
                <div class="modal-body-modern simple-modal">
                    <form id="editProfileForm" onsubmit="saveProfile(event)">
                        <!-- Personal Information Section -->
                        <div class="form-section-card">
                            <div class="form-section-header">
                                <i class="fa-solid fa-user"></i>
                                <h4>Personal Information</h4>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="editFirstName">
                                        <i class="fa-solid fa-signature" style="margin-right: 6px; color: #6b7280;"></i>
                                        First Name <span style="color: #ef4444;">*</span>
                                    </label>
                                    <input type="text" id="editFirstName" required placeholder="Enter your first name">
                                </div>
                                <div class="form-group">
                                    <label for="editLastName">
                                        <i class="fa-solid fa-signature" style="margin-right: 6px; color: #6b7280;"></i>
                                        Last Name <span style="color: #ef4444;">*</span>
                                    </label>
                                    <input type="text" id="editLastName" required placeholder="Enter your last name">
                                </div>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="editEmail">
                                        <i class="fa-solid fa-envelope" style="margin-right: 6px; color: #6b7280;"></i>
                                        Email <span style="color: #ef4444;">*</span>
                                    </label>
                                    <input type="email" id="editEmail" required placeholder="your.email@example.com">
                                </div>
                                <div class="form-group">
                                    <label for="editPhone">
                                        <i class="fa-solid fa-phone" style="margin-right: 6px; color: #6b7280;"></i>
                                        Phone Number
                                    </label>
                                    <input type="tel" id="editPhone" placeholder="+63 912 345 6789">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Business Information Section -->
                        <div class="form-section-card">
                            <div class="form-section-header">
                                <i class="fa-solid fa-briefcase"></i>
                                <h4>Business Information</h4>
                            </div>
                            <div class="form-group">
                                <label for="editBusinessName">
                                    <i class="fa-solid fa-store" style="margin-right: 6px; color: #6b7280;"></i>
                                    Business Name <span style="color: #ef4444;">*</span>
                                </label>
                                <input type="text" id="editBusinessName" required placeholder="Enter your business name">
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="editCategory">
                                        <i class="fa-solid fa-tags" style="margin-right: 6px; color: #6b7280;"></i>
                                        Business Category
                                    </label>
                                    <select id="editCategory">
                                        <option value="">Select Category</option>
                                        <option value="Fresh Produce">Fresh Produce</option>
                                        <option value="Meat & Seafood">Meat & Seafood</option>
                                        <option value="Dairy & Eggs">Dairy & Eggs</option>
                                        <option value="Bakery & Pastries">Bakery & Pastries</option>
                                        <option value="Beverages">Beverages</option>
                                        <option value="Snacks & Chips">Snacks & Chips</option>
                                        <option value="Frozen Foods">Frozen Foods</option>
                                        <option value="Canned Goods">Canned Goods</option>
                                        <option value="Condiments & Sauces">Condiments & Sauces</option>
                                        <option value="Rice & Grains">Rice & Grains</option>
                                        <option value="Noodles & Pasta">Noodles & Pasta</option>
                                        <option value="Ready-to-Eat Meals">Ready-to-Eat Meals</option>
                                        <option value="Organic & Health Foods">Organic & Health Foods</option>
                                        <option value="International Foods">International Foods</option>
                                        <option value="Other">Other</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="editBusinessEmail">
                                        <i class="fa-solid fa-envelope" style="margin-right: 6px; color: #6b7280;"></i>
                                        Business Email
                                    </label>
                                    <input type="email" id="editBusinessEmail" placeholder="business@example.com">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Profile Picture Section -->
                        <div class="form-section-card">
                            <div class="form-section-header">
                                <i class="fa-solid fa-image"></i>
                                <h4>Profile Picture</h4>
                            </div>
                            <div style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap;">
                                <div style="flex: 0 0 auto;">
                                    <div id="currentAvatarPreview" style="width: 120px; height: 120px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; border: 4px solid #e5e7eb; overflow: hidden; position: relative;">
                                        <img id="currentAvatarImg" src="" alt="Current Avatar" style="width: 100%; height: 100%; object-fit: cover; display: none;">
                                        <i class="fa-solid fa-user" style="font-size: 48px; color: white; display: block;" id="currentAvatarIcon"></i>
                                    </div>
                                </div>
                                <div style="flex: 1; min-width: 250px;">
                                    <div class="form-group" style="margin-bottom: 0;">
                                        <label for="editAvatarFile">
                                            <i class="fa-solid fa-upload" style="margin-right: 6px; color: #6b7280;"></i>
                                            Upload New Avatar
                                        </label>
                                        <input type="file" id="editAvatarFile" accept="image/*" onchange="previewAvatar(event)" style="padding: 8px;">
                                        <small style="display: block; margin-top: 6px; color: #6b7280; font-size: 12px;">
                                            <i class="fa-solid fa-info-circle"></i> Recommended: Square image, max 5MB (JPG, PNG)
                                        </small>
                                    </div>
                                    <div id="avatarPreview" style="margin-top: 16px; display: none;">
                                        <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: #f0f9ff; border-radius: 8px; border: 1px solid #bae6fd;">
                                            <img id="avatarPreviewImg" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #0ea5e9;">
                                            <div>
                                                <div style="font-weight: 600; color: #0369a1; font-size: 14px;">New Avatar Preview</div>
                                                <div style="font-size: 12px; color: #0284c7;">This will replace your current profile picture</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Form Actions -->
                        <div class="modal-actions-modern" style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb;">
                            <button type="button" class="btn btn-cancel-modern" onclick="closeEditProfileModal()" style="padding: 12px 24px; background: #f3f4f6; color: #374151; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                <i class="fa-solid fa-times"></i> Cancel
                            </button>
                            <button type="submit" class="btn btn-save-modern" style="padding: 12px 24px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                                <i class="fa-solid fa-floppy-disk"></i> Save Changes
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    loadProfileDataIntoEditModal();
}

async function loadProfileDataIntoEditModal() {
    try {
        const userResponse = await authFetch('/api/me');
        const userData = await userResponse.json();
        const sellerResponse = await authFetch('/api/seller/me');
        const sellerData = await sellerResponse.json();
        
        if (userData.success && userData.data) {
            const user = userData.data;
            const firstNameEl = document.getElementById('editFirstName');
            const lastNameEl = document.getElementById('editLastName');
            const emailEl = document.getElementById('editEmail');
            const phoneEl = document.getElementById('editPhone');
            
            if (firstNameEl) firstNameEl.value = user.first_name || '';
            if (lastNameEl) lastNameEl.value = user.last_name || '';
            if (emailEl) emailEl.value = user.email || '';
            if (phoneEl) phoneEl.value = user.phone || '';
            
            // Load current avatar
            const currentAvatarImg = document.getElementById('currentAvatarImg');
            const currentAvatarIcon = document.getElementById('currentAvatarIcon');
            if (user.avatar_url) {
                const avatarUrl = user.avatar_url.startsWith('http') ? user.avatar_url : `http://127.0.0.1:5000${user.avatar_url}`;
                if (currentAvatarImg) {
                    currentAvatarImg.src = avatarUrl;
                    currentAvatarImg.style.display = 'block';
                    if (currentAvatarIcon) currentAvatarIcon.style.display = 'none';
                }
            }
        }
        
        if (sellerData.success && sellerData.data) {
            const seller = sellerData.data;
            const businessNameEl = document.getElementById('editBusinessName');
            const categoryEl = document.getElementById('editCategory');
            const businessEmailEl = document.getElementById('editBusinessEmail');
            
            if (businessNameEl) businessNameEl.value = seller.business_name || seller.store_name || '';
            if (categoryEl) categoryEl.value = seller.category || '';
            if (businessEmailEl) businessEmailEl.value = seller.support_email || '';
        }
    } catch (error) {
        console.error('Error loading profile data into modal:', error);
    }
}

function previewAvatar(event) {
    const file = event.target.files[0];
    if (file) {
        // Validate file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            if (window.notify) {
                window.notify.error('File size must be less than 5MB');
            } else {
                alert('File size must be less than 5MB');
            }
            event.target.value = '';
            return;
        }
        
        // Validate file type
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            if (window.notify) {
                window.notify.error('Please select a valid image file (JPG, PNG, GIF, or WEBP)');
            } else {
                alert('Please select a valid image file (JPG, PNG, GIF, or WEBP)');
            }
            event.target.value = '';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('avatarPreview');
            const previewImg = document.getElementById('avatarPreviewImg');
            if (preview && previewImg) {
                previewImg.src = e.target.result;
                preview.style.display = 'block';
            }
        };
        reader.readAsDataURL(file);
    } else {
        const preview = document.getElementById('avatarPreview');
        if (preview) {
            preview.style.display = 'none';
        }
    }
}

async function saveProfile(event) {
    event.preventDefault();
    
    try {
        const formData = new FormData();
        
        // Get form values
        const firstName = document.getElementById('editFirstName').value.trim();
        const lastName = document.getElementById('editLastName').value.trim();
        const email = document.getElementById('editEmail').value.trim();
        const phone = document.getElementById('editPhone').value.trim();
        const businessName = document.getElementById('editBusinessName').value.trim();
        const category = document.getElementById('editCategory').value;
        const businessEmail = document.getElementById('editBusinessEmail').value.trim();
        const avatarFile = document.getElementById('editAvatarFile').files[0];
        
        // Validate required fields
        if (!firstName || !lastName || !email || !businessName) {
            if (window.notify) {
                window.notify.error('Please fill in all required fields');
            } else {
                alert('Please fill in all required fields');
            }
            return;
        }
        
        // Upload avatar first if provided
        let avatarUrl = null;
        if (avatarFile) {
            const avatarFormData = new FormData();
            avatarFormData.append('picture', avatarFile);
            
            const uploadResponse = await authFetch('/api/upload/profile-picture', {
                method: 'POST',
                body: avatarFormData
            });
            
            const uploadData = await uploadResponse.json();
            if (uploadData.success) {
                avatarUrl = uploadData.data?.avatar_url || uploadData.data?.file_path;
            } else {
                if (window.notify) {
                    window.notify.error('Failed to upload profile picture: ' + (uploadData.message || 'Unknown error'));
                } else {
                    alert('Failed to upload profile picture');
                }
                return;
            }
        }
        
        // Prepare update data
        const updateData = {
            first_name: firstName,
            last_name: lastName,
            email: email,
            phone: phone || null,
            business_name: businessName,
            category: category || null,
            support_email: businessEmail || null
        };
        
        if (avatarUrl) {
            updateData.avatar_url = avatarUrl;
        }
        
        // Update profile
        const updateResponse = await authFetch('/api/account/me', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        
        const updateResult = await updateResponse.json();
        
        if (updateResult.success) {
            if (window.notify) {
                window.notify.success('Profile updated successfully!');
            } else {
                alert('Profile updated successfully!');
            }
            
            closeEditProfileModal();
            await loadProfile(); // Reload profile data
            // Also update sidebar
            if (typeof loadSellerInfo === 'function') {
                loadSellerInfo();
            }
        } else {
            throw new Error(updateResult.message || 'Failed to update profile');
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        if (window.notify) {
            window.notify.error('Failed to save profile: ' + error.message);
        } else {
            alert('Failed to save profile: ' + error.message);
        }
    }
}

function closeEditProfileModal() {
    const modal = document.getElementById('editProfileModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function changePassword() {
    const modal = document.getElementById('changePasswordModal');
    if (!modal) {
        createChangePasswordModal();
    } else {
        // Clear form
        const currentPasswordEl = document.getElementById('currentPassword');
        const newPasswordEl = document.getElementById('newPassword');
        const confirmPasswordEl = document.getElementById('confirmPassword');
        const passwordErrorEl = document.getElementById('passwordError');
        
        if (currentPasswordEl) currentPasswordEl.value = '';
        if (newPasswordEl) newPasswordEl.value = '';
        if (confirmPasswordEl) confirmPasswordEl.value = '';
        if (passwordErrorEl) {
            passwordErrorEl.textContent = '';
            passwordErrorEl.style.display = 'none';
        }
        modal.style.display = 'block';
    }
}

function createChangePasswordModal() {
    const modalHTML = `
        <div id="changePasswordModal" class="modal" style="display: block;">
            <div class="modal-content modal-large modern-modal">
                <div class="modal-header-modern">
                    <div class="modal-header-content">
                        <i class="fa-solid fa-lock" aria-hidden="true" style="font-size: 24px;"></i>
                        <h2>Change Password</h2>
                    </div>
                    <button class="modal-close-modern" onclick="closeChangePasswordModal()" aria-label="Close">&times;</button>
                </div>
                <div class="modal-body-modern simple-modal">
                    <form id="changePasswordForm" onsubmit="saveNewPassword(event)">
                        <!-- Security Info Banner -->
                        <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 4px solid #3b82f6; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <i class="fa-solid fa-shield-halved" style="font-size: 20px; color: #3b82f6;"></i>
                                <div>
                                    <div style="font-weight: 600; color: #1e40af; margin-bottom: 4px;">Password Security</div>
                                    <div style="font-size: 13px; color: #1e3a8a;">For your security, you'll be logged out after changing your password.</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Password Fields Section -->
                        <div class="form-section-card">
                            <div class="form-section-header">
                                <i class="fa-solid fa-key"></i>
                                <h4>Password Information</h4>
                            </div>
                            
                            <div class="form-group">
                                <label for="currentPassword">
                                    <i class="fa-solid fa-lock" style="margin-right: 6px; color: #6b7280;"></i>
                                    Current Password <span style="color: #ef4444;">*</span>
                                </label>
                                <input type="password" id="currentPassword" required placeholder="Enter your current password" autocomplete="current-password">
                                <small style="display: block; margin-top: 6px; color: #6b7280; font-size: 12px;">
                                    <i class="fa-solid fa-info-circle"></i> Enter your existing password to verify your identity
                                </small>
                            </div>
                            
                            <div class="form-group">
                                <label for="newPassword">
                                    <i class="fa-solid fa-key" style="margin-right: 6px; color: #6b7280;"></i>
                                    New Password <span style="color: #ef4444;">*</span>
                                </label>
                                <input type="password" id="newPassword" required minlength="8" placeholder="Enter your new password" autocomplete="new-password">
                                <small style="display: block; margin-top: 6px; color: #6b7280; font-size: 12px;">
                                    <i class="fa-solid fa-shield-halved"></i> Must be at least 8 characters long. Use a mix of letters, numbers, and symbols for better security.
                                </small>
                                <div id="passwordStrength" style="margin-top: 8px; display: none;">
                                    <div style="display: flex; gap: 4px; margin-bottom: 4px;">
                                        <div id="strengthBar1" style="flex: 1; height: 4px; background: #e5e7eb; border-radius: 2px;"></div>
                                        <div id="strengthBar2" style="flex: 1; height: 4px; background: #e5e7eb; border-radius: 2px;"></div>
                                        <div id="strengthBar3" style="flex: 1; height: 4px; background: #e5e7eb; border-radius: 2px;"></div>
                                        <div id="strengthBar4" style="flex: 1; height: 4px; background: #e5e7eb; border-radius: 2px;"></div>
                                    </div>
                                    <div id="strengthText" style="font-size: 12px; font-weight: 500;"></div>
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label for="confirmPassword">
                                    <i class="fa-solid fa-check-double" style="margin-right: 6px; color: #6b7280;"></i>
                                    Confirm New Password <span style="color: #ef4444;">*</span>
                                </label>
                                <input type="password" id="confirmPassword" required minlength="8" placeholder="Re-enter your new password" autocomplete="new-password">
                                <small style="display: block; margin-top: 6px; color: #6b7280; font-size: 12px;">
                                    <i class="fa-solid fa-info-circle"></i> Re-enter your new password to confirm
                                </small>
                                <div id="passwordMatch" style="margin-top: 8px; display: none; font-size: 13px; font-weight: 500;">
                                    <i class="fa-solid fa-check-circle" style="color: #10b981;"></i>
                                    <span style="color: #10b981; margin-left: 6px;">Passwords match</span>
                                </div>
                            </div>
                            
                            <!-- Error Message -->
                            <div id="passwordError" style="display: none; padding: 12px 16px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; margin-top: 16px;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <i class="fa-solid fa-exclamation-circle" style="color: #ef4444; font-size: 18px;"></i>
                                    <div style="color: #991b1b; font-weight: 500; flex: 1;" id="passwordErrorText"></div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Form Actions -->
                        <div class="modal-actions-modern" style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb;">
                            <button type="button" class="btn btn-cancel-modern" onclick="closeChangePasswordModal()" style="padding: 12px 24px; background: #f3f4f6; color: #374151; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                <i class="fa-solid fa-times"></i> Cancel
                            </button>
                            <button type="submit" class="btn btn-save-modern" style="padding: 12px 24px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);">
                                <i class="fa-solid fa-lock"></i> Change Password
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Add password strength checker
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', checkPasswordStrength);
    }
    
    if (confirmPasswordInput && newPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    }
}

function checkPasswordStrength() {
    const password = document.getElementById('newPassword').value;
    const strengthDiv = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('strengthText');
    
    if (!password) {
        strengthDiv.style.display = 'none';
        return;
    }
    
    strengthDiv.style.display = 'block';
    
    let strength = 0;
    let strengthLabel = '';
    let strengthColor = '';
    
    // Check length
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    
    // Check for uppercase
    if (/[A-Z]/.test(password)) strength++;
    
    // Check for lowercase
    if (/[a-z]/.test(password)) strength++;
    
    // Check for numbers
    if (/[0-9]/.test(password)) strength++;
    
    // Check for special characters
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    // Determine strength level
    if (strength <= 2) {
        strengthLabel = 'Weak';
        strengthColor = '#ef4444';
    } else if (strength <= 4) {
        strengthLabel = 'Fair';
        strengthColor = '#f59e0b';
    } else if (strength <= 5) {
        strengthLabel = 'Good';
        strengthColor = '#3b82f6';
    } else {
        strengthLabel = 'Strong';
        strengthColor = '#10b981';
    }
    
    // Update strength bars
    const bars = ['strengthBar1', 'strengthBar2', 'strengthBar3', 'strengthBar4'];
    const barCount = Math.min(Math.ceil(strength / 1.5), 4);
    
    bars.forEach((barId, index) => {
        const bar = document.getElementById(barId);
        if (bar) {
            if (index < barCount) {
                bar.style.background = strengthColor;
            } else {
                bar.style.background = '#e5e7eb';
            }
        }
    });
    
    if (strengthText) {
        strengthText.textContent = `Password Strength: ${strengthLabel}`;
        strengthText.style.color = strengthColor;
    }
}

function checkPasswordMatch() {
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const matchDiv = document.getElementById('passwordMatch');
    
    if (!confirmPassword) {
        if (matchDiv) matchDiv.style.display = 'none';
        return;
    }
    
    if (newPassword === confirmPassword && newPassword.length >= 8) {
        if (matchDiv) {
            matchDiv.style.display = 'flex';
            matchDiv.style.alignItems = 'center';
        }
    } else {
        if (matchDiv) matchDiv.style.display = 'none';
    }
}

async function saveNewPassword(event) {
    event.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const errorDiv = document.getElementById('passwordError');
    const errorText = document.getElementById('passwordErrorText');
    
    // Clear previous errors
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
    if (errorText) {
        errorText.textContent = '';
    }
    
    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
        if (errorDiv && errorText) {
            errorText.textContent = 'Please fill in all fields';
            errorDiv.style.display = 'block';
        }
        return;
    }
    
    if (newPassword.length < 8) {
        if (errorDiv && errorText) {
            errorText.textContent = 'New password must be at least 8 characters long';
            errorDiv.style.display = 'block';
        }
        return;
    }
    
    if (newPassword !== confirmPassword) {
        if (errorDiv && errorText) {
            errorText.textContent = 'New passwords do not match. Please make sure both password fields are identical.';
            errorDiv.style.display = 'block';
        }
        return;
    }
    
    if (currentPassword === newPassword) {
        if (errorDiv && errorText) {
            errorText.textContent = 'New password must be different from your current password';
            errorDiv.style.display = 'block';
        }
        return;
    }
    
    try {
        const response = await authFetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (window.notify) {
                window.notify.success('Password changed successfully! You will be logged out for security.');
            } else {
                alert('Password changed successfully! You will be logged out for security.');
            }
            
            closeChangePasswordModal();
            
            // Logout after 2 seconds for security
            setTimeout(() => {
                localStorage.removeItem('hub_access_token');
                window.location.href = '/loginregister.html';
            }, 2000);
        } else {
            throw new Error(result.message || 'Failed to change password');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        if (errorDiv && errorText) {
            errorText.textContent = error.message || 'Failed to change password. Please check your current password.';
            errorDiv.style.display = 'block';
        }
    }
}

function closeChangePasswordModal() {
    const modal = document.getElementById('changePasswordModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function editBusinessInfo() {
    // Open edit profile modal and focus on business section
    editProfile();
    // Scroll to business section after modal opens
    setTimeout(() => {
        const modal = document.getElementById('editProfileModal');
        if (modal) {
            const businessSection = modal.querySelector('.form-section:nth-of-type(2)');
            if (businessSection) {
                businessSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }, 100);
}

// Expose functions globally
window.editProfile = editProfile;
window.changePassword = changePassword;
window.saveProfile = saveProfile;
window.saveNewPassword = saveNewPassword;
window.closeEditProfileModal = closeEditProfileModal;
window.closeChangePasswordModal = closeChangePasswordModal;
window.previewAvatar = previewAvatar;
window.checkPasswordStrength = checkPasswordStrength;
window.checkPasswordMatch = checkPasswordMatch;

// Revenue Management Functions
function updateRevenueReport() {
    const filter = document.getElementById('revenueFilter').value;
    const startDate = document.getElementById('revenueStartDate').value;
    const endDate = document.getElementById('revenueEndDate').value;
    
    console.log(`Updating revenue report: ${filter}, ${startDate} to ${endDate}`);
    if (window.incomeReportChart) {
        const dataObj = getIncomeData(filter, startDate, endDate);
        window.incomeReportChart.data.labels = dataObj.labels;
        window.incomeReportChart.data.datasets[0].data = dataObj.values;
        window.incomeReportChart.options.plugins.title.text = dataObj.title;
        window.incomeReportChart.update();
    }
}

function downloadTransactionHistory() {
    // Create CSV content
    const csvContent = [
        ['Date', 'Transaction ID', 'Order ID', 'Product', 'Gross Amount', 'Commission', 'Net Earnings', 'Status'],
        ['Nov 11, 2025', 'TXN-20251111-001', '#ORD-10245', 'Sample Product A', '2598.00', '311.76', '2286.24', 'Paid'],
        ['Nov 10, 2025', 'TXN-20251110-002', '#ORD-10244', 'Sample Product B', '599.00', '71.88', '527.12', 'Paid'],
        ['Nov 9, 2025', 'TXN-20251109-003', '#ORD-10243', 'Sample Product C', '2697.00', '323.64', '2373.36', 'Pending'],
        ['Nov 8, 2025', 'TXN-20251108-004', '#ORD-10242', 'Sample Product A', '1299.00', '155.88', '1143.12', 'Paid']
    ].map(row => row.join(',')).join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `transaction_history_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    alert('Transaction history downloaded successfully!');
}

async function updateCommissionBreakdown() {
    try {
        // Fetch earnings summary from backend
        const response = await authFetch('/api/sellers/earnings/summary?period=all');
        if (!response.ok) {
            console.error('Failed to load earnings summary');
            return;
        }
        
        const data = await response.json();
        if (!data.success || !data.data) {
            console.error('Invalid earnings data');
            return;
        }
        
        const earnings = data.data;
        const commissionRate = earnings.commission_rate || 10;
        
        // Update display elements
        const grossSales = earnings.gross_revenue || 0;
        const platformCommission = earnings.platform_commission || 0;
        const netEarnings = earnings.total_earnings || 0;
        
        document.getElementById('grossSales').textContent = '₱' + grossSales.toLocaleString('en-PH', { minimumFractionDigits: 2 });
        document.getElementById('platformCommission').textContent = '₱' + platformCommission.toLocaleString('en-PH', { minimumFractionDigits: 2 });
        document.getElementById('netEarnings').textContent = '₱' + netEarnings.toLocaleString('en-PH', { minimumFractionDigits: 2 });
        
        // Update rate display and examples
        document.getElementById('commissionRateDisplay').textContent = commissionRate + '%';
        document.getElementById('commissionDetails').textContent = commissionRate + '% deduction';
        document.getElementById('commissionExample').textContent = commissionRate.toFixed(0);
        document.getElementById('earningsExample').textContent = (100 - commissionRate).toFixed(0);
    } catch (err) {
        console.error('Commission breakdown error:', err);
    }
}

// Initialize charts when page loads
window.addEventListener('DOMContentLoaded', function() {
    // Multi-store functionality removed
    
    // Load initial dashboard data (this will initialize all charts with real data)
    loadDashboardData();
    
    // Calculate and display commission breakdown
    updateCommissionBreakdown();

    // Set default date range
    const today = new Date();
    const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());

    const startDateInput = document.getElementById('revenueStartDate');
    const endDateInput = document.getElementById('revenueEndDate');

    if (startDateInput) {
        startDateInput.value = lastMonth.toISOString().split('T')[0];
    }
    if (endDateInput) {
        endDateInput.value = today.toISOString().split('T')[0];
    }
    // Sync duplicate profile detail fields with main stat badges
    syncProfileStats();

    // Enable keyboard toggle for settings accordions (Enter/Space)
    document.querySelectorAll('.settings-heading').forEach(function(h) {
        h.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleSettingsGroup(h);
            }
        });
    });
});

// Data helper for income report
function getIncomeData(filter = 'monthly', startDate, endDate) {
    // Simulated revenue data sets
    const today = new Date();
    const year = today.getFullYear();
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    if (filter === 'daily') {
        // Last 14 days sample
        const labels = Array.from({ length: 14 }, (_, i) => {
            const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (13 - i));
            return (d.getMonth()+1) + '/' + d.getDate();
        });
        const values = labels.map(() => randomRange(1500, 8500));
        return sliceByDate(labels, values, startDate, endDate, 'Daily Income (Last 14 days)');
    }
    if (filter === 'weekly') {
        const labels = ['Week 1','Week 2','Week 3','Week 4','Week 5'];
        const values = labels.map(() => randomRange(25000, 60000));
        return { labels, values, title: 'Weekly Income (Current Period)' };
    }
    if (filter === 'yearly') {
        const labels = [year-4, year-3, year-2, year-1, year];
        const values = labels.map(() => randomRange(450000, 950000));
        return { labels, values, title: 'Yearly Income (Last 5 Years)' };
    }
    // Monthly default - last 12 months
    const labels = Array.from({ length: 12 }, (_, i) => monthNames[(today.getMonth() - 11 + i + 12) % 12]);
    const values = labels.map(() => randomRange(55000, 140000));
    return { labels, values, title: 'Monthly Income (Last 12 Months)' };
}

function randomRange(min, max) {
    return Math.round(Math.random() * (max - min) + min);
}

function sliceByDate(labels, values, startDate, endDate, title) {
    if (!startDate || !endDate) return { labels, values, title };
    try {
        const s = new Date(startDate);
        const e = new Date(endDate);
        const filtered = [];
        const filteredValues = [];
        labels.forEach((lab, idx) => {
            const parts = lab.split('/');
            const d = new Date(new Date().getFullYear(), parseInt(parts[0],10)-1, parseInt(parts[1],10));
            if (d >= s && d <= e) {
                filtered.push(lab);
                filteredValues.push(values[idx]);
            }
        });
        return { labels: filtered, values: filteredValues, title };
    } catch (err) {
        console.warn('Date slice error:', err);
        return { labels, values, title };
    }
}

// Profile stats synchronization
function syncProfileStats() {
    const mapping = [
        { source: 'totalOrdersValue', targets: ['detailTotalOrdersDuplicate'] },
        { source: 'totalSalesValue', targets: ['detailTotalSalesDuplicate'] },
        { source: 'ratingValue', targets: ['detailRatingDuplicate'] },
        { source: 'totalReviewsValue', targets: ['detailTotalReviewsDuplicate'] }
    ];
    mapping.forEach(entry => {
        const src = document.getElementById(entry.source);
        if (!src) return;
        entry.targets.forEach(tid => {
            const tgt = document.getElementById(tid);
            if (tgt) {
                tgt.textContent = src.textContent;
            }
        });
    });
}

// Settings Management Functions
function saveSettings() {
    // Show saving progress
    notify.info('Saving settings...');
    
    // Handle image uploads first
    const logoInput = document.getElementById('storeLogo');
    const bannerInput = document.getElementById('storeBanner');
    
    let uploadPromises = [];
    let uploadedLogPath = null;
    let uploadedBannerPath = null;
    
    // Upload logo if selected
    if (logoInput.files.length > 0) {
        const logoFormData = new FormData();
        logoFormData.append('logo', logoInput.files[0]);
        
        uploadPromises.push(
            authFetch('/api/upload/store-logo', {
                method: 'POST',
                body: logoFormData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    uploadedLogPath = data.data.path;
                } else {
                    throw new Error(data.error || 'Logo upload failed');
                }
            })
        );
    }
    
    // Upload banner if selected
    if (bannerInput.files.length > 0) {
        const bannerFormData = new FormData();
        bannerFormData.append('banner', bannerInput.files[0]);
        
        uploadPromises.push(
            authFetch('/api/upload/store-banner', {
                method: 'POST',
                body: bannerFormData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    uploadedBannerPath = data.data.path;
                } else {
                    throw new Error(data.error || 'Banner upload failed');
                }
            })
        );
    }
    
    // Wait for uploads to complete then save settings
    Promise.all(uploadPromises)
        .then(() => {
            // Gather all settings data (only include fields that exist)
            const settings = {};
            
            // Store Information
            // storeName is separate from business_name (business_name is for registration/legal)
            if (document.getElementById('storeName')) {
                settings.storeName = document.getElementById('storeName').value;
            }
            if (document.getElementById('storeDescription')) {
                settings.storeDescription = document.getElementById('storeDescription').value;
            }
            if (document.getElementById('storeCategory')) {
                settings.storeCategory = document.getElementById('storeCategory').value;
            }
            
            // Shipping Settings (from dedicated shipping tab)
            if (document.getElementById('shippingMethod')) {
                settings.shippingMethod = document.getElementById('shippingMethod').value;
            }
            if (document.getElementById('shippingFee')) {
                settings.shippingFee = document.getElementById('shippingFee').value;
            }
            if (document.getElementById('freeShippingThreshold')) {
                settings.freeShippingThreshold = document.getElementById('freeShippingThreshold').value;
            }
            
            // Notification Preferences
            if (document.getElementById('offerCOD')) {
                settings.offerCOD = document.getElementById('offerCOD').checked;
            }
            if (document.getElementById('notifyNewOrder')) {
                settings.notifyNewOrder = document.getElementById('notifyNewOrder').checked;
            }
            if (document.getElementById('notifyLowStock')) {
                settings.notifyLowStock = document.getElementById('notifyLowStock').checked;
            }
            if (document.getElementById('notifyNewReview')) {
                settings.notifyNewReview = document.getElementById('notifyNewReview').checked;
            }
            if (document.getElementById('notifyPayout')) {
                settings.notifyPayout = document.getElementById('notifyPayout').checked;
            }
            if (document.getElementById('notifyPromotion')) {
                settings.notifyPromotion = document.getElementById('notifyPromotion').checked;
            }
            
            // Business Information (secondary fields in Business Info section)
            // Skip businessName here since it's set from storeName above
            if (document.getElementById('businessAddress')) {
                settings.businessAddress = document.getElementById('businessAddress').value;
            }
            if (document.getElementById('taxId')) {
                settings.taxId = document.getElementById('taxId').value;
            }
            if (document.getElementById('businessHours')) {
                settings.businessHours = document.getElementById('businessHours').value;
            }
            
            // Security Settings
            if (document.getElementById('twoFactorAuth')) {
                settings.twoFactorAuth = document.getElementById('twoFactorAuth').checked;
            }
            if (document.getElementById('showOnlineStatus')) {
                settings.showOnlineStatus = document.getElementById('showOnlineStatus').checked;
            }
            
            // Include uploaded image paths if available
            if (uploadedLogPath) {
                settings.storeLogo = uploadedLogPath;
            }
            if (uploadedBannerPath) {
                settings.storeBanner = uploadedBannerPath;
            }
            
            // Save settings via API
            return authFetch('/api/sellers/settings', {
                method: 'POST',
                body: JSON.stringify(settings)
            });
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                notify.success('Settings saved successfully!');
                // Clear file inputs after successful save
                logoInput.value = '';
                bannerInput.value = '';
            } else {
                notify.error(data.error || 'Failed to save settings');
            }
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            notify.error(error.message || 'Error saving settings');
        });
}

// Multi-store functionality removed - single store per seller

function resetSettings() {
    if (confirm('Are you sure you want to reset all settings to default?')) {
        // Reset form fields to default values
        alert('Settings reset to default');
        location.reload();
    }
}

// Toggle accordion for settings groups
function toggleSettingsGroup(el) {
    const group = el.closest('.settings-group');
    if (!group) return;
    group.classList.toggle('collapsed');
}

function openChangePasswordModal() {
    const modal = document.getElementById('changePasswordModal');
    document.getElementById('currentPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    modal.style.display = 'block';
}

// Multi-store functionality removed - single store per seller

function resetSettings() {
    if (confirm('Are you sure you want to reset all settings to default?')) {
        // Reset form fields to default values
        alert('Settings reset to default');
        location.reload();
    }
}

// Toggle accordion for settings groups
function toggleSettingsGroup(el) {
    const group = el.closest('.settings-group');
    if (!group) return;
    group.classList.toggle('collapsed');
}

function openChangePasswordModal() {
    const modal = document.getElementById('changePasswordModal');
    document.getElementById('currentPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    modal.style.display = 'block';
}

function saveNewPassword() {
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!currentPassword || !newPassword || !confirmPassword) {
        alert('Please fill in all password fields');
        return;
    }
    
    if (newPassword.length < 8) {
        alert('New password must be at least 8 characters long');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        alert('New passwords do not match');
        return;
    }
    
    // Implement password change logic here (e.g., API call)
    alert('Password changed successfully!');
    closeModal('changePasswordModal');
}

function viewLoginHistory() {
    alert('Login History:\n\nNov 11, 2025 - 10:30 AM - Chrome on Windows\nNov 10, 2025 - 3:45 PM - Safari on iPhone\nNov 9, 2025 - 9:15 AM - Chrome on Windows');
}

// Review Management Functions
function filterReviews() {
    const searchTerm = document.getElementById('reviewSearch').value.toLowerCase();
    const reviewItems = document.querySelectorAll('.review-item');
    reviewItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

function filterReviewsByRating(rating) {
    const reviewItems = document.querySelectorAll('.review-item');
    const buttons = document.querySelectorAll('.filter-buttons .filter-btn');
    
    // Update active button
    buttons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Filter reviews
    reviewItems.forEach(item => {
        if (rating === 'all') {
            item.style.display = '';
        } else {
            const itemRating = item.getAttribute('data-rating');
            item.style.display = itemRating === rating ? '' : 'none';
        }
    });
}

function replyToReview(reviewId) {
    const modal = document.getElementById('replyReviewModal');
    document.getElementById('replyReviewId').value = reviewId;
    document.getElementById('replyText').value = '';
    modal.style.display = 'block';
}

function saveReviewReply() {
    const reviewId = document.getElementById('replyReviewId').value;
    const replyText = document.getElementById('replyText').value;
    
    if (!replyText.trim()) {
        alert('Please write a reply');
        return;
    }
    
    // Implement save logic here (e.g., API call)
    alert(`Reply sent for review ${reviewId}`);
    
    // Show the reply in the review item
    const replyDiv = document.getElementById('reply-' + reviewId);
    if (replyDiv) {
        replyDiv.querySelector('p').textContent = replyText;
        replyDiv.style.display = 'block';
    }
    
    closeModal('replyReviewModal');
}

function reportReview(reviewId) {
    const modal = document.getElementById('reportReviewModal');
    document.getElementById('reportReviewId').value = reviewId;
    document.getElementById('reportReason').value = '';
    document.getElementById('reportDetails').value = '';
    modal.style.display = 'block';
}

function submitReviewReport() {
    const reviewId = document.getElementById('reportReviewId').value;
    const reason = document.getElementById('reportReason').value;
    const details = document.getElementById('reportDetails').value;
    
    if (!reason) {
        alert('Please select a reason for reporting');
        return;
    }
    
    // Implement report logic here (e.g., API call)
    alert(`Review ${reviewId} has been reported for: ${reason}`);
    closeModal('reportReviewModal');
}

// Placeholder functions for sections not yet fully implemented
// Global earnings state
let earningsChart = null;
let currentEarningsPeriod = 'monthly';

async function loadEarnings() {
    console.log('Loading earnings data...');
    
    try {
        // Load summary, transactions, and income report in parallel
        await Promise.all([
            loadEarningsSummary(),
            loadTransactionHistory(),
            loadIncomeReport()
        ]);
        
        // Initialize date filters
        initializeEarningsFilters();
        
    } catch (error) {
        console.error('Error loading earnings:', error);
        console.error('Error details:', error.message, error.stack);
        notify.error(`Failed to load earnings data: ${error.message || 'Unknown error'}`);
    }
}

async function loadEarningsSummary(period = 'monthly') {
    try {
        const token = localStorage.getItem('hub_access_token');
        const response = await fetch(`/api/sellers/earnings/summary?period=${period}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        console.log('Earnings summary response:', data);
        console.log('Response status:', response.status);
        console.log('Full data object:', JSON.stringify(data, null, 2));
        
        if (!response.ok || !data || !data.success) {
            const errorMsg = data?.message || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMsg);
        }
        
        const earnings = data.data;
        
        // Update summary cards with null checks
        const updateElement = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };
        
        updateElement('totalEarningsSummary', `₱${formatNumber(earnings.total_earnings)}`);
        updateElement('grossRevenue', `₱${formatNumber(earnings.gross_revenue)}`);
        updateElement('platformCommission', `₱${formatNumber(earnings.platform_commission)}`);
        updateElement('pendingPayout', `₱${formatNumber(earnings.pending_payout)}`);
        updateElement('paidOut', `₱${formatNumber(earnings.paid_out)}`);
        updateElement('completedOrders', earnings.completed_orders);
        
        // Update commission breakdown cards
        updateElement('grossSales', `₱${formatNumber(earnings.gross_revenue)}`);
        updateElement('netEarnings', `₱${formatNumber(earnings.total_earnings)}`);
        
        // Update commission rate displays
        const commissionRate = earnings.commission_rate;
        updateElement('commissionRateDisplay', `${commissionRate}%`);
        updateElement('commissionDetails', `${commissionRate}% deduction`);
        
        // Update commission calculator example
        const commissionAmount = (100 * commissionRate / 100).toFixed(0);
        const earningsAmount = (100 - commissionAmount).toFixed(0);
        updateElement('commissionExample', commissionAmount);
        updateElement('earningsExample', earningsAmount);
        
        // Update earnings change indicator
        const changeElement = document.querySelector('.earning-change');
        if (changeElement && earnings.earnings_change_percent !== undefined) {
            const change = earnings.earnings_change_percent;
            changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(1)}% from last period`;
            changeElement.className = 'earning-change ' + (change >= 0 ? 'positive' : 'negative');
        }
        
        console.log('Earnings summary loaded successfully');
        
    } catch (error) {
        console.error('Error loading earnings summary:', error);
        throw error;
    }
}

async function loadTransactionHistory(page = 1, filters = {}) {
    try {
        const token = localStorage.getItem('hub_access_token');
        
        // Build query parameters
        const params = new URLSearchParams({
            page: page,
            per_page: 50
        });
        
        if (filters.status) params.append('status', filters.status);
        if (filters.start_date) params.append('start_date', filters.start_date);
        if (filters.end_date) params.append('end_date', filters.end_date);
        if (filters.order_id) params.append('order_id', filters.order_id);
        
        const response = await fetch(`/api/sellers/earnings/transactions?${params}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        console.log('Transaction history response:', data);
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load transactions');
        }
        
        const transactions = data.data.transactions;
        const tbody = document.getElementById('earningsTableBody');
        
        if (transactions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px;">
                        <i class="fa-solid fa-inbox" style="font-size: 48px; color: #ddd; margin-bottom: 10px;"></i>
                        <p style="color: #999;">No transactions found</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = transactions.map(txn => {
            const statusClass = txn.status === 'paid' ? 'status-completed' : 
                              txn.status === 'pending' ? 'status-pending' : 'status-cancelled';
            const statusText = txn.status === 'paid' ? 'Paid' : 
                             txn.status === 'pending' ? 'Pending' : 'Refunded';
            
            const date = new Date(txn.date).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            
            return `
                <tr>
                    <td>${date}</td>
                    <td>${txn.transaction_id}</td>
                    <td>#ORD-${txn.order_id}</td>
                    <td>${txn.product_name}${txn.quantity > 1 ? ` (x${txn.quantity})` : ''}</td>
                    <td>₱${formatNumber(txn.gross_amount)}</td>
                    <td class="commission-amount">₱${formatNumber(txn.commission)}</td>
                    <td class="earning-amount-cell">₱${formatNumber(txn.net_earnings)}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                </tr>
            `;
        }).join('');
        
        console.log(`Loaded ${transactions.length} transactions`);
        
    } catch (error) {
        console.error('Error loading transaction history:', error);
        throw error;
    }
}

async function loadIncomeReport(days = 30) {
    try {
        const token = localStorage.getItem('hub_access_token');
        const response = await fetch(`/api/sellers/earnings/income-report?period=daily&days=${days}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        console.log('Income report response:', data);
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to load income report');
        }
        
        const report = data.data.report;
        
        // Prepare chart data
        const labels = report.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        
        const grossRevenueData = report.map(item => item.gross_revenue);
        const commissionData = report.map(item => item.commission);
        const netEarningsData = report.map(item => item.net_earnings);
        
        // Destroy existing chart if it exists
        if (earningsChart) {
            earningsChart.destroy();
        }
        
        // Create income report chart
        const ctx = document.getElementById('incomeReportChart');
        if (ctx) {
            earningsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Gross Revenue',
                            data: grossRevenueData,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Net Earnings',
                            data: netEarningsData,
                            borderColor: '#4caf50',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'Commission',
                            data: commissionData,
                            borderColor: '#ff9800',
                            backgroundColor: 'rgba(255, 152, 0, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    label += '₱' + formatNumber(context.parsed.y);
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '₱' + formatNumber(value);
                                }
                            }
                        }
                    }
                }
            });
        }
        
        console.log('Income report loaded successfully');
        
    } catch (error) {
        console.error('Error loading income report:', error);
        throw error;
    }
}

function initializeEarningsFilters() {
    // Set default dates (last 30 days)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    const startInput = document.getElementById('revenueStartDate');
    const endInput = document.getElementById('revenueEndDate');
    
    if (startInput) startInput.valueAsDate = startDate;
    if (endInput) endInput.valueAsDate = endDate;
}

async function updateRevenueReport() {
    const filter = document.getElementById('revenueFilter').value;
    const startDate = document.getElementById('revenueStartDate').value;
    const endDate = document.getElementById('revenueEndDate').value;
    
    // Map filter to days
    let days = 30;
    if (filter === 'daily') days = 7;
    else if (filter === 'weekly') days = 28;
    else if (filter === 'monthly') days = 30;
    else if (filter === 'yearly') days = 365;
    
    // If custom date range is provided, calculate days
    if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        days = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    }
    
    try {
        await loadIncomeReport(days);
        
        // Reload summary with custom date range if provided
        if (startDate && endDate) {
            await loadTransactionHistory(1, { start_date: startDate, end_date: endDate });
        } else {
            await loadEarningsSummary(filter);
        }
        
        notify.success('Report updated successfully');
    } catch (error) {
        console.error('Error updating revenue report:', error);
        notify.error('Failed to update report');
    }
}

async function downloadTransactionHistory() {
    try {
        const token = localStorage.getItem('hub_access_token');
        const startDate = document.getElementById('revenueStartDate').value;
        const endDate = document.getElementById('revenueEndDate').value;
        
        // Build query parameters
        const params = new URLSearchParams({
            per_page: 1000  // Get all transactions for export
        });
        
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        
        const response = await fetch(`/api/sellers/earnings/transactions?${params}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'Failed to fetch transactions');
        }
        
        const transactions = data.data.transactions;
        
        // Convert to CSV
        const headers = ['Date', 'Transaction ID', 'Order ID', 'Product', 'Gross Amount', 'Commission', 'Net Earnings', 'Status'];
        const csvContent = [
            headers.join(','),
            ...transactions.map(txn => [
                new Date(txn.date).toLocaleDateString(),
                txn.transaction_id,
                `#ORD-${txn.order_id}`,
                `"${txn.product_name}"`,
                txn.gross_amount,
                txn.commission,
                txn.net_earnings,
                txn.status
            ].join(','))
        ].join('\n');
        
        // Download CSV file
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transaction_history_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        notify.success('Transaction history downloaded successfully');
        
    } catch (error) {
        console.error('Error downloading transaction history:', error);
        notify.error('Failed to download transaction history');
    }
}

function formatNumber(num) {
    return parseFloat(num).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Reviews state
let allReviews = [];
let filteredReviews = [];
let currentRatingFilter = 'all';
let currentSearchQuery = '';
let reviewsPollingInterval = null;

async function loadReviews() {
    console.log('📥 Loading product reviews data...');
    
    try {
        // Load reviews and analytics in parallel
        const [reviewsResponse, analyticsResponse] = await Promise.all([
            authFetch('/api/sellers/reviews'),
            authFetch('/api/sellers/reviews/analytics')
        ]);
        
        if (!reviewsResponse.ok) {
            const errorText = await reviewsResponse.text();
            console.error('❌ Failed to load reviews:', reviewsResponse.status, errorText);
            throw new Error(`Failed to load reviews: ${reviewsResponse.status}`);
        }
        
        const reviewsData = await reviewsResponse.json();
        console.log('📥 Reviews API response:', reviewsData);
        
        if (reviewsData.success && reviewsData.data) {
            // Filter to ensure we only have product reviews (with product_id)
            const productReviews = reviewsData.data.filter(review => {
                if (!review.product_id) {
                    console.warn('⚠️ Skipping review without product_id:', review);
                    return false;
                }
                return true;
            });
            
            console.log(`✅ Loaded ${productReviews.length} product reviews`);
            allReviews = productReviews;
            filteredReviews = [...allReviews];
            renderReviews();
        } else {
            console.log('ℹ️ No reviews data received');
            allReviews = [];
            filteredReviews = [];
            renderReviews();
        }
        
        // Load analytics
        if (analyticsResponse.ok) {
            const analyticsData = await analyticsResponse.json();
            console.log('📊 Analytics API response:', analyticsData);
            if (analyticsData.success && analyticsData.data) {
                console.log('📊 Analytics data received:', analyticsData.data);
                renderReviewAnalytics(analyticsData.data);
            } else {
                console.warn('⚠️ Analytics response missing data:', analyticsData);
            }
        } else {
            console.error('❌ Failed to load analytics:', analyticsResponse.status);
        }
        
        // Update badge after loading reviews
        if (typeof updateReviewsBadge === 'function') {
            updateReviewsBadge();
        }
        
        // Start polling for updates
        startReviewsPolling();
    } catch (err) {
        console.error('Error loading reviews:', err);
        const container = document.querySelector('.reviews-container');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #e74c3c;">
                    <i class="fa fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 16px;"></i>
                    <p>Error loading reviews. Please try again later.</p>
                </div>
            `;
        }
    }
}

function renderReviews() {
    const container = document.querySelector('.reviews-container');
    if (!container) return;
    
    if (filteredReviews.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <i class="fa fa-star" style="font-size: 64px; color: #ddd; margin-bottom: 16px;"></i>
                <h3 style="color: #666; margin-bottom: 8px;">No reviews yet</h3>
                <p style="color: #999;">When customers review your products, they will appear here.</p>
            </div>
        `;
        return;
    }
    
    // Group reviews by product
    const reviewsByProduct = {};
    filteredReviews.forEach(review => {
        const productId = review.product_id;
        if (!reviewsByProduct[productId]) {
            reviewsByProduct[productId] = {
                product_id: productId,
                product_title: review.product_title || 'Unknown Product',
                product_image: review.product_image || '',
                reviews: [],
                avg_rating: 0,
                total_reviews: 0
            };
        }
        reviewsByProduct[productId].reviews.push(review);
    });
    
    // Calculate average rating for each product
    Object.values(reviewsByProduct).forEach(product => {
        const totalRating = product.reviews.reduce((sum, r) => sum + (r.rating || 0), 0);
        product.avg_rating = totalRating / product.reviews.length;
        product.total_reviews = product.reviews.length;
    });
    
    // Sort products by average rating (descending)
    const sortedProducts = Object.values(reviewsByProduct).sort((a, b) => b.avg_rating - a.avg_rating);
    
    // Render reviews grouped by product
    container.innerHTML = sortedProducts.map(product => {
        const starsHtml = generateStarsHtml(product.avg_rating);
        
        return `
            <div class="product-review-section">
                <div class="product-review-header">
                    <div class="product-info-review">
                        <h4>${escapeHtml(product.product_title)}</h4>
                        <div class="product-rating">
                            ${starsHtml}
                            <span class="rating-avg">${product.avg_rating.toFixed(1)} / 5.0</span>
                            <span class="review-count">(${product.total_reviews} review${product.total_reviews !== 1 ? 's' : ''})</span>
                        </div>
                    </div>
                </div>
                
                <div class="reviews-list">
                    ${product.reviews.map(review => renderReviewItem(review)).join('')}
                </div>
            </div>
        `;
    }).join('');
}

function renderReviewItem(review) {
    const starsHtml = generateStarsHtml(review.rating);
    const reviewDate = new Date(review.created_at || review.updated_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
    const customerName = review.customer_name || 'Customer';
    const isRefunded = review.is_refunded || review.order_status === 'refunded';
    const refundBadge = isRefunded ? '<span class="refund-badge" title="Order was refunded, but review still counts toward metrics"><i class="fa-solid fa-undo" aria-hidden="true"></i> Refunded</span>' : '';
    
    return `
        <div class="review-item" data-rating="${review.rating}" data-product-id="${review.product_id}" data-customer-name="${escapeHtml(customerName.toLowerCase())}" data-product-name="${escapeHtml((review.product_title || '').toLowerCase())}">
            <div class="review-header">
                <div class="reviewer-info">
                    <div class="reviewer-avatar"><i class="fa-solid fa-user" aria-hidden="true"></i></div>
                    <div>
                        <strong class="reviewer-name">${escapeHtml(customerName)}</strong>
                        <div class="review-rating">
                            ${starsHtml}
                            <span class="rating-value">${review.rating}.0</span>
                            ${refundBadge}
                        </div>
                    </div>
                </div>
                <div class="review-date">${reviewDate}</div>
            </div>
            <div class="review-content">
                <p class="review-text">${escapeHtml(review.comment || 'No comment provided.')}</p>
            </div>
            <div class="review-actions">
                <button class="btn-link" onclick="replyToReview(${review.id})" aria-label="Reply to review">
                    <i class="fa-solid fa-comment-dots" aria-hidden="true"></i> Reply
                </button>
                <button class="btn-link" onclick="reportReview(${review.id})" aria-label="Report review">
                    <i class="fa-solid fa-flag" aria-hidden="true"></i> Report
                </button>
            </div>
            <div class="seller-reply" id="reply-${review.id}" style="display: none;">
                <strong>Your Reply:</strong>
                <p id="reply-text-${review.id}"></p>
            </div>
        </div>
    `;
}

function generateStarsHtml(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    let starsHtml = '';
    
    for (let i = 0; i < 5; i++) {
        if (i < fullStars) {
            starsHtml += '<i class="fa-solid fa-star"></i>';
        } else if (i === fullStars && hasHalfStar) {
            starsHtml += '<i class="fa-solid fa-star-half-stroke"></i>';
        } else {
            starsHtml += '<i class="fa-regular fa-star"></i>';
        }
    }
    
    return `<span class="rating-stars" aria-hidden="true">${starsHtml}</span>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderReviewAnalytics(analytics) {
    console.log('📊 Rendering review analytics:', analytics);
    
    // Validate analytics data
    if (!analytics) {
        console.error('❌ No analytics data provided');
        return;
    }
    
    // Update overall rating
    const overallRatingEl = document.querySelector('.reviews-summary .rating-number');
    const reviewCountEl = document.querySelector('.reviews-summary .review-count');
    const ratingStarsEl = document.querySelector('.reviews-summary .stars-large');
    
    const overallRating = parseFloat(analytics.overall_rating) || 0;
    const totalReviews = parseInt(analytics.total_reviews) || 0;
    
    if (overallRatingEl) {
        overallRatingEl.textContent = overallRating.toFixed(1);
    }
    if (reviewCountEl) {
        reviewCountEl.textContent = `Based on ${totalReviews} review${totalReviews !== 1 ? 's' : ''}`;
    }
    if (ratingStarsEl) {
        ratingStarsEl.innerHTML = generateStarsHtml(overallRating);
    }
    
    console.log(`✅ Overall rating: ${overallRating.toFixed(1)} / 5.0 (${totalReviews} reviews)`);
    
    // Update rating breakdown - REAL-TIME from actual product reviews
    console.log('📊 Updating rating breakdown with analytics:', analytics);
    const ratingBars = document.querySelectorAll('.rating-bar-item');
    
    if (!analytics.rating_breakdown) {
        console.warn('⚠️ No rating_breakdown in analytics data, using defaults');
        // Set all to 0% if no data
        ratingBars.forEach((bar) => {
            const fillEl = bar.querySelector('.rating-fill');
            const percentEl = bar.querySelector('.rating-percent');
            if (fillEl) fillEl.style.width = '0%';
            if (percentEl) percentEl.textContent = '0%';
        });
        return;
    }
    
    let totalPercentage = 0;
    ratingBars.forEach((bar, index) => {
        const rating = 5 - index; // 5, 4, 3, 2, 1
        const breakdown = analytics.rating_breakdown[rating.toString()] || {count: 0, percentage: 0};
        const fillEl = bar.querySelector('.rating-fill');
        const percentEl = bar.querySelector('.rating-percent');
        
        // Ensure percentage is a valid number (0-100)
        let percentage = parseFloat(breakdown.percentage) || 0;
        percentage = Math.max(0, Math.min(100, percentage)); // Clamp between 0 and 100
        const count = parseInt(breakdown.count) || 0;
        
        totalPercentage += percentage;
        
        console.log(`  ${rating}★: ${count} reviews (${percentage}%)`);
        
        if (fillEl) {
            fillEl.style.width = `${percentage}%`;
            fillEl.setAttribute('data-count', count);
            fillEl.setAttribute('data-percentage', percentage);
        }
        if (percentEl) {
            percentEl.textContent = `${percentage}%`;
            percentEl.setAttribute('data-count', count);
        }
    });
    
    console.log(`✅ Rating breakdown updated (total: ${totalPercentage.toFixed(1)}%)`);
    
    // Render insights
    const insightsContainer = document.getElementById('reviewInsightsContainer');
    if (insightsContainer) {
        insightsContainer.innerHTML = `
            <div class="insights-grid">
                <div class="insight-card">
                    <div class="insight-icon" style="background: #e8f5e9;">
                        <i class="fa fa-heart" style="color: #4caf50;"></i>
                    </div>
                    <div class="insight-content">
                        <h4>Customer Satisfaction</h4>
                        <p class="insight-value">${analytics.satisfaction_score || 0}%</p>
                        <p class="insight-label">Positive reviews (4★ & 5★)</p>
                    </div>
                </div>
                
                <div class="insight-card">
                    <div class="insight-icon" style="background: #fff3e0;">
                        <i class="fa fa-keywords" style="color: #ff9800;"></i>
                    </div>
                    <div class="insight-content">
                        <h4>Most Mentioned</h4>
                        <div class="keywords-list">
                            ${analytics.top_keywords && analytics.top_keywords.length > 0
                                ? analytics.top_keywords.slice(0, 5).map(k => `<span class="keyword-tag">${escapeHtml(k.word)} (${k.count})</span>`).join('')
                                : '<p style="color: #999; font-size: 14px;">No keywords yet</p>'
                            }
                        </div>
                    </div>
                </div>
                
                <div class="insight-card">
                    <div class="insight-icon" style="background: #fce4ec;">
                        <i class="fa fa-chart-line" style="color: #e91e63;"></i>
                    </div>
                    <div class="insight-content">
                        <h4>Areas to Improve</h4>
                        <div class="improvements-list">
                            ${analytics.areas_to_improve && analytics.areas_to_improve.length > 0
                                ? analytics.areas_to_improve.map(a => `<span class="improvement-tag">${escapeHtml(a.word)}</span>`).join('')
                                : '<p style="color: #999; font-size: 14px;">No specific areas identified</p>'
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

function filterReviews() {
    const searchInput = document.getElementById('reviewSearch');
    if (!searchInput) return;
    
    currentSearchQuery = searchInput.value.toLowerCase().trim();
    applyFilters();
}

function filterReviewsByRating(rating) {
    currentRatingFilter = rating;
    
    // Update active button
    document.querySelectorAll('.filter-buttons .filter-btn').forEach(btn => {
        btn.classList.remove('active');
        // Check if this button matches the rating filter
        const btnText = btn.textContent.trim();
        if (rating === 'all' && btnText === 'All') {
            btn.classList.add('active');
        } else if (btnText.includes(rating)) {
            btn.classList.add('active');
        }
    });
    
    applyFilters();
}

function applyFilters() {
    filteredReviews = allReviews.filter(review => {
        // Rating filter
        if (currentRatingFilter !== 'all' && review.rating.toString() !== currentRatingFilter) {
            return false;
        }
        
        // Search filter
        if (currentSearchQuery) {
            const productName = (review.product_title || '').toLowerCase();
            const customerName = (review.customer_name || '').toLowerCase();
            const comment = (review.comment || '').toLowerCase();
            
            if (!productName.includes(currentSearchQuery) &&
                !customerName.includes(currentSearchQuery) &&
                !comment.includes(currentSearchQuery)) {
                return false;
            }
        }
        
        return true;
    });
    
    renderReviews();
}

// Auto-refresh reviews when reviews section is active
function startReviewsPolling() {
    // Clear any existing polling
    if (reviewsPollingInterval) {
        clearInterval(reviewsPollingInterval);
    }
    
    // Only poll if reviews section is active
    const reviewsSection = document.getElementById('reviewsSection');
    if (reviewsSection && reviewsSection.classList.contains('active')) {
        reviewsPollingInterval = setInterval(() => {
            // Only reload if section is still active
            if (reviewsSection.classList.contains('active')) {
                loadReviews();
            } else {
                stopReviewsPolling();
            }
        }, 30000); // Poll every 30 seconds
    }
}

function stopReviewsPolling() {
    if (reviewsPollingInterval) {
        clearInterval(reviewsPollingInterval);
        reviewsPollingInterval = null;
    }
}

// Expose functions globally
window.loadReviews = loadReviews;
window.filterReviews = filterReviews;
window.filterReviewsByRating = filterReviewsByRating;
window.startReviewsPolling = startReviewsPolling;
window.stopReviewsPolling = stopReviewsPolling;
window.replyToReview = function(reviewId) {
    // TODO: Implement reply functionality
    console.log('Reply to review:', reviewId);
    if (window.notify) {
        notify.info('Reply functionality coming soon');
    }
};
window.reportReview = function(reviewId) {
    // TODO: Implement report functionality
    console.log('Report review:', reviewId);
    if (window.notify) {
        notify.info('Report functionality coming soon');
    }
};

async function loadProfile() {
    try {
        console.log('Loading seller profile data...');
        
        // Load user account info
        const userResponse = await authFetch('/api/me');
        const userData = await userResponse.json();
        
        if (!userData.success) {
            console.error('Failed to load user data:', userData);
            return;
        }
        
        const user = userData.data || {};
        
        // Load seller info
        const sellerResponse = await authFetch('/api/seller/me');
        const sellerData = await sellerResponse.json();
        
        if (!sellerData.success) {
            console.error('Failed to load seller data:', sellerData);
            return;
        }
        
        const seller = sellerData.data || {};
        
        // Load profile stats
        const statsResponse = await authFetch('/api/seller/profile/stats');
        const statsData = await statsResponse.json();
        
        const stats = statsData.success ? statsData.data : {
            total_orders: 0,
            total_earnings: 0,
            average_rating: 0,
            rating_count: 0,
            member_since: null
        };
        
        // Update Profile Header
        const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email || 'Seller';
        document.getElementById('profileFullName').textContent = fullName;
        document.getElementById('profileEmail').textContent = user.email || '-';
        
        // Update Avatar
        const profileAvatarImg = document.getElementById('profileAvatarImg');
        const profileAvatarLarge = document.getElementById('profileAvatarLarge');
        if (user.avatar_url) {
            const avatarUrl = user.avatar_url.startsWith('http') ? user.avatar_url : `http://127.0.0.1:5000${user.avatar_url}`;
            if (profileAvatarImg) {
                profileAvatarImg.src = avatarUrl;
                profileAvatarImg.style.display = '';
                const fallback = profileAvatarLarge?.querySelector('.avatar-fallback');
                if (fallback) fallback.style.display = 'none';
            }
        }
        
        // Update Rating
        const ratingCount = stats.rating_count || 0;
        const avgRating = stats.average_rating || 0;
        const profileStars = document.getElementById('profileStars');
        const profileRatingCount = document.getElementById('profileRatingCount');
        
        if (profileRatingCount) {
            profileRatingCount.textContent = `(${ratingCount} ${ratingCount === 1 ? 'rating' : 'ratings'})`;
        }
        
        if (profileStars) {
            const stars = profileStars.querySelectorAll('.fa-star');
            stars.forEach((star, index) => {
                if (index < Math.round(avgRating)) {
                    star.classList.add('filled');
                    star.style.color = '#ffc107';
                } else {
                    star.classList.remove('filled');
                    star.style.color = '#ddd';
                }
            });
        }
        
        // Update Stats
        document.getElementById('detailTotalOrders').textContent = stats.total_orders || 0;
        document.getElementById('detailTotalEarnings').textContent = `₱${(stats.total_earnings || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        
        const memberSince = stats.member_since ? new Date(stats.member_since).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '-';
        document.getElementById('detailMemberSince').textContent = memberSince;
        
        // Update Business Information
        document.getElementById('detailBusinessName').textContent = seller.business_name || seller.store_name || '-';
        document.getElementById('detailCategory').textContent = seller.category || '-';
        document.getElementById('detailEmail').textContent = user.email || seller.support_email || '-';
        
        const statusBadge = document.getElementById('detailStatus');
        if (statusBadge) {
            const shopStatus = seller.shop_status || 'pending';
            statusBadge.textContent = shopStatus.charAt(0).toUpperCase() + shopStatus.slice(1);
            statusBadge.className = 'status-badge';
            if (shopStatus === 'active') {
                statusBadge.style.backgroundColor = '#10b981';
                statusBadge.style.color = 'white';
            } else if (shopStatus === 'pending') {
                statusBadge.style.backgroundColor = '#f59e0b';
                statusBadge.style.color = 'white';
            } else {
                statusBadge.style.backgroundColor = '#ef4444';
                statusBadge.style.color = 'white';
            }
        }
        
        // Update Account Information (duplicate stats)
        document.getElementById('detailTotalOrdersDuplicate').textContent = stats.total_orders || 0;
        document.getElementById('detailTotalEarningsDuplicate').textContent = `₱${(stats.total_earnings || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        document.getElementById('detailMemberSinceDuplicate').textContent = memberSince;
        
        // Update Online Status (based on last_login)
        const onlineStatus = document.getElementById('detailOnlineStatus');
        if (onlineStatus && user.last_login) {
            const lastLogin = new Date(user.last_login);
            const now = new Date();
            const hoursSinceLogin = (now - lastLogin) / (1000 * 60 * 60);
            if (hoursSinceLogin < 24) {
                onlineStatus.textContent = 'Active';
                onlineStatus.style.color = '#10b981';
            } else {
                onlineStatus.textContent = 'Inactive';
                onlineStatus.style.color = '#6b7280';
            }
        } else if (onlineStatus) {
            onlineStatus.textContent = 'Active';
            onlineStatus.style.color = '#10b981';
        }
        
        console.log('Profile data loaded successfully');
    } catch (error) {
        console.error('Error loading profile:', error);
        if (window.notify) {
            window.notify.error('Failed to load profile data. Please refresh the page.');
        }
    }
}

// Messenger functionality
let currentConversationId = 1;
const conversations = [
    { customerId: 1, customerName: 'Maria Santos', orderRef: 'Order #10245', unread: true, important: false },
    { customerId: 2, customerName: 'Juan Dela Cruz', orderRef: 'Order #10244', unread: true, important: false },
    { customerId: 3, customerName: 'Ana Reyes', orderRef: 'Order #10243', unread: false, important: false }
];

function updateUnreadMessagesBadge() {
    // This function is deprecated - now handled by seller-messaging.js
    // Keep for backward compatibility but do nothing
    console.log('Legacy updateUnreadMessagesBadge called - now handled by seller-messaging.js');
}

function openConversationLegacy(customerId) {
    // Legacy function - kept for backward compatibility
    // New messaging system uses openSellerConversation from seller-messaging.js
    console.log('Legacy openConversation called - use openSellerConversation instead');
    
    currentConversationId = customerId;
    
    // Update active conversation in list
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.classList.remove('active');
        if (parseInt(item.getAttribute('data-customer-id')) === customerId) {
            item.classList.add('active');
            item.classList.remove('unread');
        }
    });
    
    // Mark as read
    const conversation = conversations.find(c => c.customerId === customerId);
    if (conversation) {
        conversation.unread = false;
        updateUnreadMessagesBadge();
        
        // Update chat header
        document.getElementById('chatCustomerName').textContent = conversation.customerName;
        document.getElementById('chatOrderRef').textContent = conversation.orderRef;
    }
    
    // In a real app, load messages from backend
    console.log('Opened conversation with customer:', customerId);
}

function filterConversations() {
    const searchTerm = document.getElementById('conversationSearch').value.toLowerCase();
    const items = document.querySelectorAll('.conversation-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(searchTerm) ? 'flex' : 'none';
    });
}

function filterMessagesByStatus(status) {
    // Update active tab
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    const items = document.querySelectorAll('.conversation-item');
    
    items.forEach(item => {
        if (status === 'all') {
            item.style.display = 'flex';
        } else if (status === 'unread') {
            item.style.display = item.classList.contains('unread') ? 'flex' : 'none';
        } else if (status === 'important') {
            // In real app, check important flag
            item.style.display = 'none';
        }
    });
}

function sendMessageLegacy() {
    // Legacy function - kept for backward compatibility
    // New messaging system uses sendSellerMessage from seller-messaging.js
    console.log('Legacy sendMessage called - use sendSellerMessage instead');
    
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add message to chat
    const chatMessages = document.getElementById('chatMessages');
    const messageTime = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    const messageHTML = `
        <div class="message seller-message">
            <div class="message-content">
                <div class="message-bubble">
                    <p>${escapeHtml(message)}</p>
                </div>
                <span class="message-timestamp">${messageTime}</span>
            </div>
        </div>
    `;
    
    chatMessages.insertAdjacentHTML('beforeend', messageHTML);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Clear input
    input.value = '';
    
    // In real app, send to backend via API
    console.log('Message sent:', message);
}

function handleMessageKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function insertQuickReply(text) {
    document.getElementById('messageInput').value = text;
    document.getElementById('messageInput').focus();
}

function toggleQuickReplies() {
    const quickReplies = document.getElementById('quickReplies');
    quickReplies.classList.toggle('show');
}

function attachFile() {
    // In real app, open file picker
    alert('File attachment feature - would open file picker in production');
}

function toggleImportantFlag() {
    const conversation = conversations.find(c => c.customerId === currentConversationId);
    if (conversation) {
        conversation.important = !conversation.important;
        alert(conversation.important ? 'Marked as important' : 'Removed important flag');
        // Update UI accordingly
    }
}

// Removed duplicate viewOrderDetails function - using the one defined earlier that properly loads order details

function archiveConversation() {
    if (confirm('Archive this conversation?')) {
        alert('Conversation archived');
        // In real app, update backend and refresh list
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize unread messages badge when page loads
if (typeof updateUnreadMessagesBadge === 'function') {
    updateUnreadMessagesBadge();
}

// Image Upload and Preview Handler
document.addEventListener('DOMContentLoaded', function() {
    // Image input change is now handled by handleProductImageChange function
    // No need for duplicate event listener here
    
    // Store Logo Preview Handler
    const logoInput = document.getElementById('storeLogo');
    if (logoInput) {
        logoInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'];
                if (!allowedTypes.includes(file.type)) {
                    notify.error('Invalid file type. Only JPG, PNG, WEBP, and GIF are allowed.');
                    logoInput.value = '';
                    document.getElementById('logoPreview').style.display = 'none';
                    return;
                }
                
                // Validate file size (5MB max)
                const maxSize = 5 * 1024 * 1024; // 5MB in bytes
                if (file.size > maxSize) {
                    notify.error('File too large. Maximum size is 5MB.');
                    logoInput.value = '';
                    document.getElementById('logoPreview').style.display = 'none';
                    return;
                }
                
                // Show preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewImg = document.getElementById('logoPreviewImg');
                    const previewDiv = document.getElementById('logoPreview');
                    previewImg.src = e.target.result;
                    previewDiv.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Store Banner Preview Handler
    const bannerInput = document.getElementById('storeBanner');
    if (bannerInput) {
        bannerInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
                if (!allowedTypes.includes(file.type)) {
                    notify.error('Invalid file type. Only JPG, PNG, and WEBP are allowed.');
                    bannerInput.value = '';
                    document.getElementById('bannerPreview').style.display = 'none';
                    return;
                }
                
                // Validate file size (10MB max)
                const maxSize = 10 * 1024 * 1024; // 10MB in bytes
                if (file.size > maxSize) {
                    notify.error('File too large. Maximum size is 10MB.');
                    bannerInput.value = '';
                    document.getElementById('bannerPreview').style.display = 'none';
                    return;
                }
                
                // Show preview
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewImg = document.getElementById('bannerPreviewImg');
                    const previewDiv = document.getElementById('bannerPreview');
                    previewImg.src = e.target.result;
                    previewDiv.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
});

// Add more JS as needed for dynamic data and charts

// ============================================
// SHIPPING SETTINGS FUNCTIONS
// ============================================

/**
 * Load current shipping settings for the seller
 */
async function loadShippingSettings() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.error('No auth token found');
            return;
        }

        const response = await fetch('http://localhost:5000/api/seller/settings/shipping', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            
            // Populate form fields with current values
            const thresholdInput = document.getElementById('freeShippingThreshold');
            const feeInput = document.getElementById('standardShippingFee');
            
            if (thresholdInput && data.free_shipping_threshold !== null) {
                thresholdInput.value = parseFloat(data.free_shipping_threshold).toFixed(2);
            }
            
            if (feeInput && data.standard_shipping_fee !== null) {
                feeInput.value = parseFloat(data.standard_shipping_fee).toFixed(2);
            }
            
            console.log('Shipping settings loaded:', data);
        } else if (response.status === 401) {
            console.error('Unauthorized - redirecting to login');
            window.location.href = 'loginregister.html';
        } else {
            const error = await response.json();
            console.error('Failed to load shipping settings:', error);
        }
    } catch (error) {
        console.error('Error loading shipping settings:', error);
    }
}

/**
 * Load seller info to populate settings form
 */
async function loadSellerInfo() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.error('No auth token found for seller info');
            return;
        }

        // Fetch current seller's info using /api/seller/me endpoint
        const response = await authFetch('/api/seller/me');
        if (response.ok) {
            const seller = await response.json();
            
            // Populate storeName field (use store_name if available, fallback to business_name)
            const storeNameInput = document.getElementById('storeName');
            if (storeNameInput) {
                storeNameInput.value = seller.store_name || seller.business_name || '';
            }
            
            // Populate store description
            const storeDescInput = document.getElementById('storeDescription');
            if (storeDescInput && seller.store_description) {
                storeDescInput.value = seller.store_description;
            }
            
            // Populate category
            const storeCategorySelect = document.getElementById('storeCategory');
            if (storeCategorySelect && seller.category) {
                storeCategorySelect.value = seller.category;
            }
            
            // Show current logo if exists
            if (seller.store_logo) {
                const logoPreview = document.getElementById('currentLogoPreview');
                if (logoPreview) {
                    logoPreview.src = seller.store_logo;
                    logoPreview.style.display = 'block';
                }
            }
            
            // Show current banner if exists
            if (seller.store_banner) {
                const bannerPreview = document.getElementById('currentBannerPreview');
                if (bannerPreview) {
                    bannerPreview.src = seller.store_banner;
                    bannerPreview.style.display = 'block';
                }
            }
        }
    } catch (error) {
        console.error('Error loading seller info:', error);
    }
}

/**
 * Save shipping settings for the seller
 */
async function saveShippingSettings() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            showShippingMessage('Please log in to save settings', 'error');
            return;
        }

        const thresholdInput = document.getElementById('freeShippingThreshold');
        const feeInput = document.getElementById('standardShippingFee');
        const messageDiv = document.getElementById('shippingSettingsMessage');

        // Get values
        const threshold = parseFloat(thresholdInput.value);
        const fee = parseFloat(feeInput.value);

        // Validate inputs
        if (isNaN(threshold) || threshold < 0) {
            showShippingMessage('Please enter a valid free shipping threshold (0 or greater)', 'error');
            thresholdInput.focus();
            return;
        }

        if (isNaN(fee) || fee < 0) {
            showShippingMessage('Please enter a valid shipping fee (0 or greater)', 'error');
            feeInput.focus();
            return;
        }

        // Check reasonable limits
        if (fee > 10000) {
            showShippingMessage('Shipping fee cannot exceed ₱10,000 per item', 'error');
            feeInput.focus();
            return;
        }

        if (threshold > 1000000) {
            showShippingMessage('Free shipping threshold cannot exceed ₱1,000,000', 'error');
            thresholdInput.focus();
            return;
        }

        // Show loading state
        showShippingMessage('Saving settings...', 'info');

        const response = await fetch('http://localhost:5000/api/seller/settings/shipping', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                free_shipping_threshold: threshold,
                standard_shipping_fee: fee
            })
        });

        if (response.ok) {
            const data = await response.json();
            showShippingMessage(data.message || 'Shipping settings saved successfully!', 'success');
            
            // Update form with saved values (rounded)
            thresholdInput.value = parseFloat(data.settings.free_shipping_threshold).toFixed(2);
            feeInput.value = parseFloat(data.settings.standard_shipping_fee).toFixed(2);
            
            console.log('Shipping settings saved:', data);
        } else if (response.status === 401) {
            showShippingMessage('Session expired. Please log in again.', 'error');
            setTimeout(() => {
                window.location.href = 'loginregister.html';
            }, 2000);
        } else {
            const error = await response.json();
            showShippingMessage(error.error || 'Failed to save shipping settings', 'error');
        }
    } catch (error) {
        console.error('Error saving shipping settings:', error);
        showShippingMessage('Network error. Please check your connection.', 'error');
    }
}

/**
 * Display a message in the shipping settings section
 */
function showShippingMessage(message, type) {
    const messageDiv = document.getElementById('shippingSettingsMessage');
    if (!messageDiv) return;

    messageDiv.textContent = message;
    messageDiv.style.display = 'block';

    // Style based on type
    if (type === 'success') {
        messageDiv.style.backgroundColor = '#d4edda';
        messageDiv.style.color = '#155724';
        messageDiv.style.borderLeft = '4px solid #28a745';
    } else if (type === 'error') {
        messageDiv.style.backgroundColor = '#f8d7da';
        messageDiv.style.color = '#721c24';
        messageDiv.style.borderLeft = '4px solid #dc3545';
    } else if (type === 'info') {
        messageDiv.style.backgroundColor = '#d1ecf1';
        messageDiv.style.color = '#0c5460';
        messageDiv.style.borderLeft = '4px solid #17a2b8';
    }

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}

// Greeting Message Functions
async function loadGreetingMessage() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            console.error('No auth token found');
            return;
        }

        // Get seller ID first
        const sellerResponse = await authFetch('/api/account/me');
        const sellerData = await sellerResponse.json();
        
        if (!sellerData.success || !sellerData.data || !sellerData.data.seller || !sellerData.data.seller.id) {
            console.error('Could not get seller ID');
            return;
        }

        const sellerId = sellerData.data.seller.id;

        const response = await authFetch(`/api/sellers/${sellerId}/greeting`, {
            method: 'GET'
        });

        if (response.ok) {
            const data = await response.json();
            const greetingInput = document.getElementById('greetingMessage');
            
            if (greetingInput && data.success && data.data) {
                greetingInput.value = data.data.greeting_message || 'Hello! Thank you for your interest. How can I help you today?';
            }
        }
    } catch (error) {
        console.error('Error loading greeting message:', error);
    }
}

async function saveGreetingMessage() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            showGreetingMessage('Please log in to save greeting message', 'error');
            return;
        }

        const greetingInput = document.getElementById('greetingMessage');
        const statusDiv = document.getElementById('greetingMessageStatus');

        if (!greetingInput) {
            showGreetingMessage('Greeting message input not found', 'error');
            return;
        }

        const greetingText = greetingInput.value.trim();

        // Validate length
        if (greetingText.length > 500) {
            showGreetingMessage('Greeting message is too long (max 500 characters)', 'error');
            greetingInput.focus();
            return;
        }

        // Save greeting message
        const response = await authFetch('/api/sellers/greeting', {
            method: 'PUT',
            body: JSON.stringify({
                greeting_message: greetingText
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showGreetingMessage('Greeting message saved successfully!', 'success');
        } else {
            showGreetingMessage(data.message || 'Failed to save greeting message', 'error');
        }
    } catch (error) {
        console.error('Error saving greeting message:', error);
        showGreetingMessage('Failed to save greeting message. Please try again.', 'error');
    }
}

function showGreetingMessage(message, type) {
    const statusDiv = document.getElementById('greetingMessageStatus');
    if (!statusDiv) return;

    statusDiv.style.display = 'block';
    statusDiv.className = type === 'success' ? 'success-message' : 'error-message';
    statusDiv.textContent = message;
    statusDiv.style.padding = '10px';
    statusDiv.style.borderRadius = '4px';
    statusDiv.style.marginTop = '10px';

    if (type === 'success') {
        statusDiv.style.backgroundColor = '#d4edda';
        statusDiv.style.color = '#155724';
        statusDiv.style.border = '1px solid #c3e6cb';
    } else {
        statusDiv.style.backgroundColor = '#f8d7da';
        statusDiv.style.color = '#721c24';
        statusDiv.style.border = '1px solid #f5c6cb';
    }

    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

// Expose functions globally
window.loadGreetingMessage = loadGreetingMessage;

// ==================== NOTIFICATION BADGES ====================

let badgeUpdateInterval = null;

/**
 * Update Orders badge count
 */
async function updateOrdersBadge() {
    try {
        const response = await authFetch('/api/sellers/orders/new-count');
        if (!response.ok) {
            console.warn('Failed to fetch new orders count');
            return;
        }
        
        const data = await response.json();
        const count = data.success && data.data ? data.data.new_orders_count : 0;
        
        const badge = document.getElementById('ordersBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error updating orders badge:', error);
    }
}

/**
 * Update Reviews badge count
 */
async function updateReviewsBadge() {
    try {
        const response = await authFetch('/api/sellers/reviews/new-count');
        if (!response.ok) {
            console.warn('Failed to fetch new reviews count');
            return;
        }
        
        const data = await response.json();
        const count = data.success && data.data ? data.data.new_reviews_count : 0;
        
        const badge = document.getElementById('reviewsBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error updating reviews badge:', error);
    }
}

/**
 * Update all notification badges
 */
async function updateAllBadges() {
    await Promise.all([
        updateOrdersBadge(),
        updateReviewsBadge(),
        updateSellerUnreadBadge ? updateSellerUnreadBadge() : Promise.resolve()
    ]);
}

/**
 * Show login notification with summary of new activity
 */
async function showLoginNotification() {
    try {
        const response = await authFetch('/api/sellers/notifications/summary');
        if (!response.ok) {
            return; // Silently fail if summary not available
        }
        
        const data = await response.json();
        if (!data.success || !data.data) {
            return;
        }
        
        const { new_orders, new_reviews, unread_messages } = data.data;
        
        // Only show notification if there's something new
        if (new_orders === 0 && new_reviews === 0 && unread_messages === 0) {
            return;
        }
        
        // Create notification banner
        const notification = document.createElement('div');
        notification.id = 'loginNotification';
        notification.className = 'login-notification';
        notification.innerHTML = `
            <div class="login-notification-content">
                <div class="login-notification-header">
                    <i class="fa fa-bell"></i>
                    <h3>Welcome back! You have new activity:</h3>
                    <button class="login-notification-close" onclick="this.closest('.login-notification').remove()">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
                <div class="login-notification-items">
                    ${new_orders > 0 ? `
                        <div class="login-notification-item">
                            <i class="fa fa-shopping-cart"></i>
                            <span><strong>${new_orders}</strong> new order${new_orders !== 1 ? 's' : ''}</span>
                            <a href="javascript:void(0);" onclick="switchSection('orders'); document.getElementById('loginNotification')?.remove();">View</a>
                        </div>
                    ` : ''}
                    ${new_reviews > 0 ? `
                        <div class="login-notification-item">
                            <i class="fa fa-star"></i>
                            <span><strong>${new_reviews}</strong> new review${new_reviews !== 1 ? 's' : ''}</span>
                            <a href="javascript:void(0);" onclick="switchSection('reviews'); document.getElementById('loginNotification')?.remove();">View</a>
                        </div>
                    ` : ''}
                    ${unread_messages > 0 ? `
                        <div class="login-notification-item">
                            <i class="fa fa-message"></i>
                            <span><strong>${unread_messages}</strong> unread message${unread_messages !== 1 ? 's' : ''}</span>
                            <a href="javascript:void(0);" onclick="switchSection('messages'); document.getElementById('loginNotification')?.remove();">View</a>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        document.body.insertBefore(notification, document.body.firstChild);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            const notif = document.getElementById('loginNotification');
            if (notif) {
                notif.style.opacity = '0';
                setTimeout(() => notif.remove(), 300);
            }
        }, 10000);
        
    } catch (error) {
        console.error('Error showing login notification:', error);
    }
}

/**
 * Start badge polling
 */
function startBadgePolling() {
    // Clear existing interval if any
    if (badgeUpdateInterval) {
        clearInterval(badgeUpdateInterval);
    }
    
    // Update badges immediately
    updateAllBadges();
    
    // Then update every 30 seconds
    badgeUpdateInterval = setInterval(() => {
        updateAllBadges();
    }, 30000); // 30 seconds
}

/**
 * Stop badge polling
 */
function stopBadgePolling() {
    if (badgeUpdateInterval) {
        clearInterval(badgeUpdateInterval);
        badgeUpdateInterval = null;
    }
}

// Expose functions globally
window.updateOrdersBadge = updateOrdersBadge;
window.updateReviewsBadge = updateReviewsBadge;
window.updateAllBadges = updateAllBadges;
window.showLoginNotification = showLoginNotification;
window.startBadgePolling = startBadgePolling;
window.stopBadgePolling = stopBadgePolling;
window.saveGreetingMessage = saveGreetingMessage;

