// ============== Admin Sales Approval System ==============

let pendingSales = [];
let currentSaleForAction = null;
let currentSalesFilter = 'pending'; // Track current filter

// Initialize when sales section is loaded
async function loadPendingSales(filterType = 'pending') {
    console.log(`Loading sales with filter: ${filterType}...`);
    
    // Update current filter
    currentSalesFilter = filterType;
    
    try {
        // Always fetch fresh data with cache-busting
        const timestamp = Date.now();
        const response = await authFetch(`/api/admin/pending-sales?filter=${filterType}&t=${timestamp}`, {
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to load sales: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`Sales data (filter: ${filterType}):`, data);
        
        if (data.success && data.data) {
            pendingSales = data.data;
            updateSalesStats();
            displayPendingSales(pendingSales, filterType);
        } else {
            throw new Error(data.message || 'Invalid response');
        }
    } catch (error) {
        console.error('Error loading sales:', error);
        const container = document.getElementById('pendingSalesContainer');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 60px 20px; color: #f44336;">
                    <div style="font-size: 48px; margin-bottom: 20px; opacity: 0.5;">
                        <i class="fas fa-exclamation-circle"></i>
                    </div>
                    <p style="font-size: 18px; margin-bottom: 10px; font-weight: 600;">Failed to Load Sales</p>
                    <p style="font-size: 14px; color: #666;">Error: ${error.message}</p>
                    <button onclick="loadPendingSales('${filterType}')" style="margin-top: 20px; padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">
                        <i class="fas fa-sync"></i> Retry
                    </button>
                </div>
            `;
        }
    }
}

// Filter sales by status
window.filterSalesByStatus = function(filterType, buttonElement) {
    console.log(`Filtering sales by: ${filterType}`);
    
    // Update active button state
    document.querySelectorAll('[data-sales-filter]').forEach(btn => {
        btn.classList.remove('active');
    });
    if (buttonElement) {
        buttonElement.classList.add('active');
    } else {
        // Find button by data attribute if element not provided
        const btn = document.querySelector(`[data-sales-filter="${filterType}"]`);
        if (btn) btn.classList.add('active');
    }
    
    // Load sales with the selected filter (fresh API call, no cache)
    loadPendingSales(filterType);
    
    // Update stats after loading (to ensure counts are accurate)
    setTimeout(() => {
        updateSalesStats();
    }, 500);
};

// Update unified empty state based on both sales and discounts
function updateUnifiedEmptyState() {
    // Check if sales container is visible (it gets hidden when empty)
    const salesContainer = document.getElementById('pendingSalesContainer');
    const hasSales = salesContainer && salesContainer.style.display !== 'none' && pendingSales && pendingSales.length > 0;
    
    // Check if discount container is visible (it gets hidden when empty)
    const discountContainer = document.getElementById('discountApprovalsContainer');
    const hasDiscounts = discountContainer && discountContainer.style.display !== 'none';
    
    let emptyStateContainer = document.getElementById('unifiedEmptyState');
    
    if (!hasSales && !hasDiscounts) {
        // Create or show unified empty state
        if (!emptyStateContainer) {
            emptyStateContainer = document.createElement('div');
            emptyStateContainer.id = 'unifiedEmptyState';
            const salesContainer = document.getElementById('pendingSalesContainer');
            if (salesContainer && salesContainer.parentNode) {
                salesContainer.parentNode.insertBefore(emptyStateContainer, salesContainer);
            }
        }
        emptyStateContainer.style.display = 'block';
        emptyStateContainer.innerHTML = `
            <div style="text-align: center; padding: 80px 20px; background: white; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.3; color: #27ae60;">
                    <i class="fas fa-check-circle"></i>
                </div>
                <p style="font-size: 24px; margin-bottom: 10px; font-weight: 600; color: #2c3e50;">All Caught Up!</p>
                <p style="font-size: 16px; color: #7f8c8d;">No pending sale or discount requests at the moment</p>
                <p style="font-size: 14px; color: #95a5a6; margin-top: 8px;">New requests will appear here when sellers submit them</p>
            </div>
        `;
    } else if (emptyStateContainer) {
        // Hide empty state when we have content
        emptyStateContainer.style.display = 'none';
    }
}

// Update sales statistics by fetching counts from API
async function updateSalesStats() {
    try {
        // Fetch counts for each filter type in parallel (fresh data, no cache)
        const timestamp = Date.now();
        const [pendingRes, approvedTodayRes, rejectedRes, criticalRes] = await Promise.all([
            authFetch(`/api/admin/pending-sales?filter=pending&t=${timestamp}`, { cache: 'no-store' }),
            authFetch(`/api/admin/pending-sales?filter=approved_today&t=${timestamp}`, { cache: 'no-store' }),
            authFetch(`/api/admin/pending-sales?filter=rejected&t=${timestamp}`, { cache: 'no-store' }),
            authFetch(`/api/admin/pending-sales?filter=critical&t=${timestamp}`, { cache: 'no-store' })
        ]);
        
        // Parse responses
        const pendingData = pendingRes.ok ? await pendingRes.json() : { data: [] };
        const approvedTodayData = approvedTodayRes.ok ? await approvedTodayRes.json() : { data: [] };
        const rejectedData = rejectedRes.ok ? await rejectedRes.json() : { data: [] };
        const criticalData = criticalRes.ok ? await criticalRes.json() : { data: [] };
        
        const pending = (pendingData.data || []).length;
        const approvedToday = (approvedTodayData.data || []).length;
        const rejected = (rejectedData.data || []).length;
        const critical = (criticalData.data || []).length;
        
        // Update sidebar badge
        const badge = document.getElementById('pendingSalesBadge');
        if (badge) {
            badge.textContent = pending;
            badge.style.display = pending > 0 ? 'inline-block' : 'none';
        }
        
        // Update stat cards
        const pendingCount = document.getElementById('pendingSalesCount');
        if (pendingCount) pendingCount.textContent = pending;
        
        const approvedTodayCount = document.getElementById('approvedTodayCount');
        if (approvedTodayCount) approvedTodayCount.textContent = approvedToday;
        
        const rejectedCount = document.getElementById('rejectedSalesCount');
        if (rejectedCount) rejectedCount.textContent = rejected;
        
        const criticalCount = document.getElementById('criticalSalesCount');
        if (criticalCount) criticalCount.textContent = critical;
        
        console.log('Sales stats updated:', { pending, approvedToday, rejected, critical });
    } catch (error) {
        console.error('Error updating sales stats:', error);
        // Fallback to local counts if API fails
        const pending = pendingSales.filter(s => s.status === 'pending').length;
        const critical = pendingSales.filter(s => s.days_until_expiry <= 3 && s.status === 'pending').length;
        
        const pendingCount = document.getElementById('pendingSalesCount');
        if (pendingCount) pendingCount.textContent = pending;
        
        const criticalCount = document.getElementById('criticalSalesCount');
        if (criticalCount) criticalCount.textContent = critical;
    }
}

function displayPendingSales(sales, filterType = 'pending') {
    const container = document.getElementById('pendingSalesContainer');
    if (!container) return;
    
    // Hide unified empty state when we have sales to display
    const unifiedEmptyState = document.getElementById('unifiedEmptyState');
    if (unifiedEmptyState) {
        unifiedEmptyState.style.display = 'none';
    }
    
    if (!sales || sales.length === 0) {
        // Hide the container when empty - let updateUnifiedEmptyState handle the empty message
        container.style.display = 'none';
        // Update unified empty state (will show if both sales and discounts are empty)
        updateUnifiedEmptyState();
        return;
    }
    
    // Show container when we have sales
    container.style.display = 'block';
    
    // Sort by urgency (critical items first, then by days until expiry)
    const sortedSales = [...sales].sort((a, b) => {
        // Critical items first (days_until_expiry <= 3)
        const aCritical = (a.days_until_expiry || 999) <= 3 && a.status === 'pending';
        const bCritical = (b.days_until_expiry || 999) <= 3 && b.status === 'pending';
        if (aCritical && !bCritical) return -1;
        if (!aCritical && bCritical) return 1;
        // Then by days until expiry
        return (a.days_until_expiry || 999) - (b.days_until_expiry || 999);
    });
    
    const cardsHTML = sortedSales.map(sale => createSaleCard(sale, filterType)).join('');
    
    container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px;">
            ${cardsHTML}
        </div>
    `;
    
    // Update unified empty state (will hide it since we have sales)
    updateUnifiedEmptyState();
}

function createSaleCard(sale, filterType = 'pending') {
    const urgency = getUrgencyLevel(sale.days_until_expiry || 999);
    const urgencyColors = {
        critical: { bg: '#ffebee', border: '#f44336', text: '#c62828' },
        high: { bg: '#fff3e0', border: '#ff9800', text: '#e65100' },
        medium: { bg: '#fff9c4', border: '#fdd835', text: '#f57f17' },
        low: { bg: '#e8f5e9', border: '#66bb6a', text: '#2e7d32' }
    };
    
    const colors = urgencyColors[urgency.level];
    
    // Calculate profit metrics (already calculated in backend, but ensure we have values)
    const sellerMarginPercent = parseFloat(sale.seller_profit_margin || 0).toFixed(1);
    const platformCommissionPercent = parseFloat(sale.platform_commission || 7.5).toFixed(1);
    const sellerProfit = parseFloat(sale.seller_profit || 0);
    const estimatedCost = parseFloat(sale.estimated_cost || (sale.original_price * 0.65));
    
    // Determine profit warning level
    const hasNegativeProfit = sellerProfit < 0;
    const hasLowMargin = parseFloat(sellerMarginPercent) < 10 && !hasNegativeProfit;
    
    // Show action buttons only for pending/review items
    const showActions = (filterType === 'pending' || filterType === 'review' || filterType === 'critical') && sale.status === 'pending';
    
    // Show rejection reason for rejected items
    const rejectionReason = (sale.status === 'rejected' || sale.status === 'declined') && sale.admin_notes ? `
        <div style="background: #ffebee; border-left: 4px solid #f44336; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
            <div style="font-size: 12px; font-weight: 700; color: #c62828; margin-bottom: 5px; text-transform: uppercase;">
                <i class="fas fa-times-circle"></i> Rejection Reason
            </div>
            <div style="font-size: 13px; color: #d32f2f;">${sale.admin_notes || sale.rejection_reason || 'No reason provided'}</div>
        </div>
    ` : '';
    
    // Show approval info for approved items
    const approvalInfo = sale.status === 'approved' && sale.admin_approved_at ? `
        <div style="background: #e8f5e9; border-left: 4px solid #4caf50; padding: 12px; border-radius: 6px; margin-bottom: 15px;">
            <div style="font-size: 12px; font-weight: 700; color: #2e7d32; margin-bottom: 5px; text-transform: uppercase;">
                <i class="fas fa-check-circle"></i> Approved
            </div>
            <div style="font-size: 13px; color: #388e3c;">
                Approved on ${new Date(sale.admin_approved_at).toLocaleDateString()} at ${new Date(sale.admin_approved_at).toLocaleTimeString()}
            </div>
        </div>
    ` : '';
    
    return `
        <div class="admin-sale-card" style="background: white; border: 2px solid ${colors.border}; border-radius: 12px; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s;">
            <!-- Header with Urgency -->
            <div style="background: ${colors.bg}; padding: 15px; border-bottom: 2px solid ${colors.border};">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="background: ${colors.border}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; text-transform: uppercase;">
                            ${urgency.label}
                        </span>
                        <span style="color: ${colors.text}; font-size: 13px; font-weight: 600;">
                            <i class="fas fa-clock"></i> ${sale.days_until_expiry} days left
                        </span>
                    </div>
                </div>
                <div style="font-size: 16px; font-weight: 700; color: #2c3e50;">
                    ${sale.product_title || sale.product_name || 'Product #' + sale.product_id}
                </div>
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 3px;">
                    Seller: ${sale.seller_name || sale.seller_email || 'Unknown'} • Requested ${formatTimeAgo(sale.seller_requested_at || sale.created_at)}
                </div>
                ${sale.expiry_date ? `
                <div style="font-size: 12px; color: #7f8c8d; margin-top: 5px;">
                    <i class="fas fa-calendar-alt"></i> Expiry Date: ${new Date(sale.expiry_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                </div>
                ` : ''}
            </div>
            
            <!-- Pricing Details -->
            <div style="padding: 20px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div>
                        <div style="font-size: 11px; color: #95a5a6; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">Original Price</div>
                        <div style="font-size: 20px; font-weight: 700; color: #7f8c8d; text-decoration: line-through;">₱${sale.original_price.toFixed(2)}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: #95a5a6; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;">Sale Price</div>
                        <div style="font-size: 20px; font-weight: 700; color: #27ae60;">₱${sale.sale_price.toFixed(2)}</div>
                    </div>
                </div>
                
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                    <div style="font-size: 13px; font-weight: 600; color: #2c3e50; margin-bottom: 8px;">
                        <i class="fas fa-percentage"></i> Discount: ${sale.discount_percentage}%
                    </div>
                    <div style="font-size: 12px; color: #7f8c8d;">
                        Customer saves: <strong style="color: #e74c3c;">₱${(sale.original_price - sale.sale_price).toFixed(2)}</strong>
                    </div>
                </div>
                
                <!-- Profit Analysis -->
                <div style="background: linear-gradient(135deg, #667eea15, #764ba215); border: 1px solid #667eea; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                    <div style="font-size: 12px; font-weight: 700; color: #667eea; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">
                        <i class="fas fa-chart-line"></i> Profit Impact Analysis
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <div style="font-size: 11px; color: #7f8c8d; margin-bottom: 3px;">Seller Margin</div>
                            <div style="font-size: 16px; font-weight: 700; color: ${sellerMarginPercent >= 10 ? '#27ae60' : '#e74c3c'};">
                                ${sellerMarginPercent}%
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #7f8c8d; margin-bottom: 3px;">Platform Commission</div>
                            <div style="font-size: 16px; font-weight: 700; color: #667eea;">
                                ${platformCommissionPercent}%
                            </div>
                        </div>
                    </div>
                    ${hasNegativeProfit ? `
                        <div style="margin-top: 10px; padding: 10px; background: #ffebee; border-left: 4px solid #f44336; border-radius: 4px;">
                            <div style="font-size: 12px; color: #c62828; font-weight: 700;">
                                <i class="fas fa-exclamation-circle"></i> <strong>❗ Negative Profit Detected:</strong> This discount would result in a loss of ₱${Math.abs(sellerProfit).toFixed(2)}
                            </div>
                            <div style="font-size: 11px; color: #d32f2f; margin-top: 5px;">
                                Estimated cost: ₱${estimatedCost.toFixed(2)} | Seller revenue after commission: ₱${(sale.seller_revenue || (sale.sale_price * 0.925)).toFixed(2)}
                            </div>
                        </div>
                    ` : hasLowMargin ? `
                        <div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;">
                            <div style="font-size: 12px; color: #856404; font-weight: 600;">
                                <i class="fas fa-exclamation-triangle"></i> <strong>⚠️ Low Profit Warning:</strong> Seller margin (${sellerMarginPercent}%) is below recommended 10%
                            </div>
                            <div style="font-size: 11px; color: #856404; margin-top: 5px;">
                                Estimated profit: ₱${sellerProfit.toFixed(2)} | Consider reviewing this request
                            </div>
                        </div>
                    ` : ''}
                </div>
                
                ${rejectionReason}
                ${approvalInfo}
                
                ${showActions ? `
                <!-- Action Buttons -->
                <div style="display: flex; gap: 10px;">
                    <button onclick="approveSale(${sale.id})" 
                            style="flex: 1; padding: 12px; background: linear-gradient(135deg, #4caf50, #388e3c); color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.3s; box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(76, 175, 80, 0.4)'"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(76, 175, 80, 0.3)'"
                            ${hasNegativeProfit ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
                        <i class="fas fa-check-circle"></i> Approve
                    </button>
                    <button onclick="openReviewModal(${sale.id})" 
                            style="flex: 1; padding: 12px; background: linear-gradient(135deg, #ff9800, #f57c00); color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.3s; box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(255, 152, 0, 0.4)'"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(255, 152, 0, 0.3)'">
                        <i class="fas fa-eye"></i> Review
                    </button>
                    <button onclick="openRejectModal(${sale.id})" 
                            style="flex: 1; padding: 12px; background: linear-gradient(135deg, #f44336, #d32f2f); color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.3s; box-shadow: 0 2px 8px rgba(244, 67, 54, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(244, 67, 54, 0.4)'"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(244, 67, 54, 0.3)'">
                        <i class="fas fa-times-circle"></i> Reject
                    </button>
                </div>
                ` : `
                <!-- Status Badge (for non-pending items) -->
                <div style="text-align: center; padding: 12px; background: ${sale.status === 'approved' ? '#e8f5e9' : '#ffebee'}; border-radius: 8px; border: 2px solid ${sale.status === 'approved' ? '#4caf50' : '#f44336'};">
                    <span style="color: ${sale.status === 'approved' ? '#2e7d32' : '#c62828'}; font-weight: 700; font-size: 14px; text-transform: uppercase;">
                        ${sale.status === 'approved' ? '<i class="fas fa-check-circle"></i> Approved' : '<i class="fas fa-times-circle"></i> Rejected'}
                    </span>
                </div>
                `}
            </div>
        </div>
    `;
}

function getUrgencyLevel(daysUntilExpiry) {
    // Fix urgency levels: Critical (1-3), High (4-7), Medium (8-14), Low (>14)
    const days = daysUntilExpiry || 999;
    if (days >= 1 && days <= 3) {
        return { level: 'critical', label: 'Critical' };
    } else if (days >= 4 && days <= 7) {
        return { level: 'high', label: 'High' };
    } else if (days >= 8 && days <= 14) {
        return { level: 'medium', label: 'Medium' };
    } else {
        return { level: 'low', label: 'Low' };
    }
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return 'recently';
    
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return past.toLocaleDateString();
}

async function approveSale(saleId) {
    if (!confirm('Approve this sale request? The product price will be updated to the sale price immediately.')) {
        return;
    }
    
    try {
        const response = await authFetch(`/api/admin/sales/${saleId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (typeof notify !== 'undefined') {
                notify.success('Sale approved successfully! Product price updated and seller has been notified.');
            } else {
                alert('Sale approved successfully!');
            }
            
            // Reload sales with current filter
            await loadPendingSales(currentSalesFilter);
            // Update stats
            await updateSalesStats();
        } else {
            throw new Error(data.message || 'Failed to approve sale');
        }
    } catch (error) {
        console.error('Error approving sale:', error);
        if (typeof notify !== 'undefined') {
            notify.error('Failed to approve sale: ' + error.message);
        } else {
            alert('Error: ' + error.message);
        }
    }
}

function openReviewModal(saleId) {
    currentSaleForAction = saleId;
    
    const modal = document.createElement('div');
    modal.id = 'adminReviewSaleModal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 10000; animation: fadeIn 0.2s;';
    
    modal.innerHTML = `
        <div style="background: white; border-radius: 16px; max-width: 500px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideUp 0.3s;">
            <div style="background: linear-gradient(135deg, #ff9800, #f57c00); color: white; padding: 25px; border-radius: 16px 16px 0 0;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="width: 50px; height: 50px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-eye" style="font-size: 24px;"></i>
                    </div>
                    <div>
                        <h2 style="margin: 0; font-size: 24px;">Request Review</h2>
                        <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">Ask seller for clarification or adjustments</p>
                    </div>
                </div>
            </div>
            
            <div style="padding: 30px;">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 10px; color: #2c3e50; font-weight: 600; font-size: 15px;">
                        <i class="fas fa-comment-alt"></i> Review Notes *
                    </label>
                    <textarea id="adminReviewNotes" rows="5" 
                              style="width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-family: inherit; font-size: 14px; resize: vertical; transition: border-color 0.3s;"
                              placeholder="Enter what needs clarification or adjustment (e.g., discount too high, profit margin too low, pricing error, etc.)"
                              onfocus="this.style.borderColor='#ff9800'"
                              onblur="this.style.borderColor='#e0e0e0'"></textarea>
                    <small style="display: block; margin-top: 5px; color: #95a5a6;">This will be sent to the seller for review and revision</small>
                </div>
                
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button onclick="closeReviewModal()" 
                            style="padding: 12px 24px; background: #ecf0f1; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; color: #7f8c8d; transition: all 0.3s;"
                            onmouseover="this.style.background='#bdc3c7'"
                            onmouseout="this.style.background='#ecf0f1'">
                        Cancel
                    </button>
                    <button onclick="confirmReviewSale()" 
                            style="padding: 12px 24px; background: linear-gradient(135deg, #ff9800, #f57c00); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; transition: all 0.3s; box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(255, 152, 0, 0.4)'"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 152, 0, 0.3)'">
                        <i class="fas fa-check"></i> Mark for Review
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
}

function closeReviewModal() {
    const modal = document.getElementById('adminReviewSaleModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
    currentSaleForAction = null;
}

async function confirmReviewSale() {
    const notes = document.getElementById('adminReviewNotes').value.trim();
    
    if (!notes) {
        if (typeof notify !== 'undefined') {
            notify.error('Please provide review notes');
        } else {
            alert('Please provide review notes');
        }
        return;
    }
    
    if (!currentSaleForAction) {
        console.error('No sale ID for review');
        return;
    }
    
    try {
        const response = await authFetch(`/api/admin/sales/${currentSaleForAction}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes || 'Needs clarification from seller' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (typeof notify !== 'undefined') {
                notify.success('Sale request marked for review. Seller will be notified.');
            } else {
                alert('Sale request marked for review successfully!');
            }
            
            closeReviewModal();
            
            // Reload sales with current filter
            await loadPendingSales(currentSalesFilter);
            // Update stats
            await updateSalesStats();
        } else {
            throw new Error(data.message || 'Failed to mark sale for review');
        }
    } catch (error) {
        console.error('Error marking sale for review:', error);
        if (typeof notify !== 'undefined') {
            notify.error('Failed to mark sale for review: ' + error.message);
        } else {
            alert('Error: ' + error.message);
        }
    }
}

function openRejectModal(saleId) {
    currentSaleForAction = saleId;
    
    const modal = document.createElement('div');
    modal.id = 'adminRejectSaleModal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 10000; animation: fadeIn 0.2s;';
    
    modal.innerHTML = `
        <div style="background: white; border-radius: 16px; max-width: 500px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideUp 0.3s;">
            <div style="background: linear-gradient(135deg, #f44336, #d32f2f); color: white; padding: 25px; border-radius: 16px 16px 0 0;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="width: 50px; height: 50px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-times-circle" style="font-size: 24px;"></i>
                    </div>
                    <div>
                        <h2 style="margin: 0; font-size: 24px;">Reject Sale Request</h2>
                        <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">Provide a reason for the seller</p>
                    </div>
                </div>
            </div>
            
            <div style="padding: 30px;">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 10px; color: #2c3e50; font-weight: 600; font-size: 15px;">
                        <i class="fas fa-comment-alt"></i> Rejection Reason *
                    </label>
                    <textarea id="adminRejectNotes" rows="5" 
                              style="width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-family: inherit; font-size: 14px; resize: vertical; transition: border-color 0.3s;"
                              placeholder="Enter reason for rejection (e.g., discount too high, insufficient profit margin, pricing error, etc.)"
                              onfocus="this.style.borderColor='#667eea'"
                              onblur="this.style.borderColor='#e0e0e0'"></textarea>
                    <small style="display: block; margin-top: 5px; color: #95a5a6;">This will be sent to the seller for transparency</small>
                </div>
                
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button onclick="closeRejectModal()" 
                            style="padding: 12px 24px; background: #ecf0f1; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; color: #7f8c8d; transition: all 0.3s;"
                            onmouseover="this.style.background='#bdc3c7'"
                            onmouseout="this.style.background='#ecf0f1'">
                        Cancel
                    </button>
                    <button onclick="confirmRejectSale()" 
                            style="padding: 12px 24px; background: linear-gradient(135deg, #f44336, #d32f2f); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; display: flex; align-items: center; gap: 8px; transition: all 0.3s; box-shadow: 0 4px 12px rgba(244, 67, 54, 0.3);"
                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(244, 67, 54, 0.4)'"
                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(244, 67, 54, 0.3)'">
                        <i class="fas fa-check"></i> Confirm Rejection
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
}

function closeRejectModal() {
    const modal = document.getElementById('adminRejectSaleModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
    currentSaleForAction = null;
}

async function confirmRejectSale() {
    const notes = document.getElementById('adminRejectNotes').value.trim();
    
    if (!notes) {
        if (typeof notify !== 'undefined') {
            notify.error('Please provide a reason for rejection');
        } else {
            alert('Please provide a reason for rejection');
        }
        return;
    }
    
    if (!currentSaleForAction) {
        console.error('No sale ID for rejection');
        return;
    }
    
    try {
        const response = await authFetch(`/api/admin/sales/${currentSaleForAction}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ admin_notes: notes })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (typeof notify !== 'undefined') {
                notify.success('Sale request rejected. Seller has been notified.');
            } else {
                alert('Sale request rejected successfully!');
            }
            
            closeRejectModal();
            
            // Reload sales with current filter
            await loadPendingSales(currentSalesFilter);
            // Update stats
            await updateSalesStats();
        } else {
            throw new Error(data.message || 'Failed to reject sale');
        }
    } catch (error) {
        console.error('Error rejecting sale:', error);
        if (typeof notify !== 'undefined') {
            notify.error('Failed to reject sale: ' + error.message);
        } else {
            alert('Error: ' + error.message);
        }
    }
}

// Auto-load when sales section is shown
// We'll hook into the switchSection function or use event delegation
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the sales section initially
    const salesSection = document.getElementById('salesSection');
    if (salesSection && salesSection.classList.contains('active')) {
        // Load pending sales and update stats
        loadPendingSales('pending');
        updateSalesStats();
    }
});

// Expose functions globally
window.loadPendingSales = loadPendingSales;
window.filterSalesByStatus = filterSalesByStatus;
window.updateSalesStats = updateSalesStats;
window.approveSale = approveSale;
window.openReviewModal = openReviewModal;
window.closeReviewModal = closeReviewModal;
window.confirmReviewSale = confirmReviewSale;
window.openRejectModal = openRejectModal;
window.closeRejectModal = closeRejectModal;
window.confirmRejectSale = confirmRejectSale;
