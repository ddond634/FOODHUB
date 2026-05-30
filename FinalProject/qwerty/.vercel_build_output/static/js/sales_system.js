/**
 * Sales System - Seller Dashboard Integration
 * Handles expiring product alerts and sale requests
 */

// Reuse global API_BASE if set; prevent duplicate const declaration errors
if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = window.location.origin;
}
if (typeof API_BASE === 'undefined') {
    var API_BASE = window.API_BASE;
}

// Load sale suggestions for expiring products
async function loadSaleSuggestions() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;

        const response = await fetch(`${API_BASE}/api/sellers/sale-suggestions`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();
        
        if (data.success && data.data && data.data.suggestions) {
            displaySaleSuggestions(data.data.suggestions);
        }
    } catch (error) {
        console.error('Error loading sale suggestions:', error);
    }
}

function displaySaleSuggestions(suggestions) {
    const container = document.getElementById('saleSuggestionsContainer');
    if (!container) return;

    if (suggestions.length === 0) {
        container.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">No expiring products found</p>';
        return;
    }

    const html = suggestions.map(item => `
        <div class="sale-suggestion-card" data-product-id="${item.product_id}">
            <div class="sale-header">
                <div class="sale-urgency ${getUrgencyClass(item.days_until_expiry)}">
                    <i class="fa fa-clock"></i> ${item.days_until_expiry} day${item.days_until_expiry > 1 ? 's' : ''} until expiry
                </div>
            </div>
            
            <div class="sale-product-info">
                <h4>${escapeHtml(item.product_title)}</h4>
                <div class="sale-pricing">
                    <div class="price-row">
                        <span class="label">Current Price:</span>
                        <span class="value">₱${item.current_price.toFixed(2)}</span>
                    </div>
                    <div class="price-row suggested">
                        <span class="label">Suggested Discount:</span>
                        <span class="value">${item.suggested_discount}%</span>
                    </div>
                    <div class="price-row sale">
                        <span class="label">Suggested Sale Price:</span>
                        <span class="value">₱${item.sale_price.toFixed(2)}</span>
                    </div>
                </div>
                
                <div class="profit-analysis">
                    <div class="profit-row">
                        <i class="fa fa-coins"></i>
                        <span>Your Profit Margin: <strong>${item.seller_profit_margin.toFixed(1)}%</strong></span>
                    </div>
                    <div class="profit-row">
                        <i class="fa fa-chart-line"></i>
                        <span>Platform Fee: <strong>${item.platform_commission_pct.toFixed(1)}%</strong></span>
                    </div>
                    <div class="profit-row">
                        <i class="fa fa-money-bill-wave"></i>
                        <span>Your Revenue: <strong>₱${item.seller_revenue.toFixed(2)}</strong> per unit</span>
                    </div>
                </div>
                
                <div class="sale-rationale">
                    <i class="fa fa-info-circle"></i> ${item.rationale}
                </div>
                
                <div class="sale-actions">
                    <button class="btn-request-sale" onclick="requestSale(${item.product_id}, ${item.suggested_discount})">
                        <i class="fa fa-tag"></i> Request Sale
                    </button>
                    <button class="btn-custom-sale" onclick="openCustomSaleModal(${item.product_id}, ${item.current_price}, ${item.suggested_discount})">
                        <i class="fa fa-edit"></i> Custom Discount
                    </button>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

function getUrgencyClass(days) {
    if (days <= 3) return 'urgent-critical';
    if (days <= 7) return 'urgent-high';
    if (days <= 10) return 'urgent-medium';
    return 'urgent-low';
}

async function requestSale(productId, discountPct) {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) {
            alert('Please log in');
            return;
        }

        const response = await fetch(`${API_BASE}/api/sellers/products/${productId}/request-sale`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                discount_percentage: discountPct,
                reason: 'expiring_soon'
            })
        });

        const data = await response.json();
        
        if (data.success) {
            if (window.notify) {
                notify.success('Sale request submitted! Waiting for admin approval.');
            } else {
                alert('Sale request submitted successfully!');
            }
            // Reload suggestions
            loadSaleSuggestions();
        } else {
            if (window.notify) {
                notify.error(data.error || 'Failed to request sale');
            } else {
                alert(data.error || 'Failed to request sale');
            }
        }
    } catch (error) {
        console.error('Request sale error:', error);
        alert('Error submitting sale request');
    }
}

function openCustomSaleModal(productId, currentPrice, suggestedDiscount) {
    const modal = document.getElementById('customSaleModal');
    if (!modal) {
        createCustomSaleModal();
        return openCustomSaleModal(productId, currentPrice, suggestedDiscount);
    }

    document.getElementById('customSaleProductId').value = productId;
    document.getElementById('customSaleCurrentPrice').textContent = currentPrice.toFixed(2);
    document.getElementById('customSaleSuggested').textContent = suggestedDiscount;
    document.getElementById('customDiscountInput').value = suggestedDiscount;
    
    // Update preview
    updateCustomSalePreview(currentPrice);
    
    modal.hidden = false;
}

function createCustomSaleModal() {
    const modalHTML = `
        <div id="customSaleModal" class="modal" hidden>
            <div class="modal-overlay" onclick="closeCustomSaleModal()"></div>
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h3>Request Custom Discount</h3>
                    <button class="modal-close" onclick="closeCustomSaleModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <input type="hidden" id="customSaleProductId">
                    
                    <div class="form-group">
                        <label>Current Price:</label>
                        <div class="price-display">₱<span id="customSaleCurrentPrice">0.00</span></div>
                    </div>
                    
                    <div class="form-group">
                        <label>Suggested Discount:</label>
                        <div class="discount-display"><span id="customSaleSuggested">0</span>%</div>
                    </div>
                    
                    <div class="form-group">
                        <label>Your Discount (1-50%):</label>
                        <input type="number" id="customDiscountInput" min="1" max="50" step="0.5" 
                               oninput="updateCustomSalePreview(parseFloat(document.getElementById('customSaleCurrentPrice').textContent))">
                        <small>Maximum 50% discount allowed</small>
                    </div>
                    
                    <div class="sale-preview" id="customSalePreview">
                        <!-- Preview will be inserted here -->
                    </div>
                    
                    <div class="modal-actions">
                        <button class="btn-cancel" onclick="closeCustomSaleModal()">Cancel</button>
                        <button class="btn-submit" onclick="submitCustomSale()">Submit Request</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function updateCustomSalePreview(currentPrice) {
    const discountInput = document.getElementById('customDiscountInput');
    const preview = document.getElementById('customSalePreview');
    
    const discount = parseFloat(discountInput.value) || 0;
    const salePrice = currentPrice * (1 - discount / 100);
    const savings = currentPrice - salePrice;
    
    preview.innerHTML = `
        <h4>Preview:</h4>
        <div class="preview-row">
            <span>Sale Price:</span>
            <strong>₱${salePrice.toFixed(2)}</strong>
        </div>
        <div class="preview-row">
            <span>Customer Saves:</span>
            <strong>₱${savings.toFixed(2)} (${discount}%)</strong>
        </div>
        <div class="preview-note">
            <i class="fa fa-info-circle"></i> 
            This request requires admin approval before becoming active.
        </div>
    `;
}

function closeCustomSaleModal() {
    const modal = document.getElementById('customSaleModal');
    if (modal) modal.hidden = true;
}

async function submitCustomSale() {
    const productId = document.getElementById('customSaleProductId').value;
    const discount = parseFloat(document.getElementById('customDiscountInput').value);
    
    if (!discount || discount < 1 || discount > 50) {
        alert('Please enter a valid discount between 1% and 50%');
        return;
    }
    
    await requestSale(productId, discount);
    closeCustomSaleModal();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// Load existing sales for seller
async function loadExistingSales() {
    try {
        const token = localStorage.getItem('hub_access_token');
        if (!token) return;

        const response = await fetch(`${API_BASE}/api/sellers/sales`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();
        
        if (data.success && data.data) {
            displayExistingSales(data.data);
            // Update badge count
            const badge = document.getElementById('salesCountBadge');
            if (badge) {
                const count = data.data.length;
                badge.textContent = count;
                badge.style.display = count > 0 ? 'inline-block' : 'none';
            }
        } else {
            displayExistingSales([]);
        }
    } catch (error) {
        console.error('Error loading existing sales:', error);
        displayExistingSales([]);
    }
}

function displayExistingSales(sales) {
    const container = document.getElementById('existingSalesContainer');
    if (!container) return;

    if (sales.length === 0) {
        container.innerHTML = '<p style="color: #666; text-align: center; padding: 40px;">No sales found. Create a sale request from the suggestions tab.</p>';
        return;
    }

    const html = sales.map(sale => {
        const status = sale.status || 'pending';
        const statusClass = status === 'approved' ? 'status-approved' : status === 'rejected' ? 'status-rejected' : 'status-pending';
        const statusText = status.charAt(0).toUpperCase() + status.slice(1);
        
        const productImage = sale.product_image 
            ? (sale.product_image.startsWith('http') ? sale.product_image : `http://127.0.0.1:5000${sale.product_image}`)
            : 'https://via.placeholder.com/100';
        
        const validUntil = sale.valid_until ? new Date(sale.valid_until).toLocaleDateString() : 'No expiry';
        
        return `
            <div class="existing-sale-card" data-sale-id="${sale.id}">
                <div class="sale-card-header">
                    <div class="sale-product-image">
                        <img src="${productImage}" alt="${escapeHtml(sale.product_title || 'Product')}" onerror="this.src='https://via.placeholder.com/100'">
                    </div>
                    <div class="sale-card-info">
                        <h4>${escapeHtml(sale.product_title || 'Unknown Product')}</h4>
                        <div class="sale-status-badge ${statusClass}">${statusText}</div>
                    </div>
                </div>
                
                <div class="sale-card-details">
                    <div class="detail-row">
                        <span class="label">Original Price:</span>
                        <span class="value">₱${parseFloat(sale.original_price || 0).toFixed(2)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Discount:</span>
                        <span class="value discount">-${parseFloat(sale.discount_percentage || 0).toFixed(1)}%</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Sale Price:</span>
                        <span class="value sale-price">₱${parseFloat(sale.sale_price || 0).toFixed(2)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Valid Until:</span>
                        <span class="value">${validUntil}</span>
                    </div>
                    ${sale.admin_notes ? `
                    <div class="detail-row">
                        <span class="label">Admin Notes:</span>
                        <span class="value">${escapeHtml(sale.admin_notes)}</span>
                    </div>
                    ` : ''}
                </div>
                
                <div class="sale-card-actions">
                    ${status === 'pending' ? `
                        <button class="btn-edit-sale" onclick="editSale(${sale.id})">
                            <i class="fa fa-edit"></i> Edit
                        </button>
                        <button class="btn-delete-sale" onclick="deleteSale(${sale.id})">
                            <i class="fa fa-trash"></i> Remove
                        </button>
                    ` : `
                        <span class="action-disabled">${status === 'approved' ? 'Sale is active' : 'Cannot modify ' + statusText.toLowerCase() + ' sales'}</span>
                    `}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function switchSalesTab(tab) {
    const suggestionsTab = document.getElementById('suggestionsTab');
    const existingTab = document.getElementById('existingTab');
    const suggestionsContainer = document.getElementById('saleSuggestionsContainer');
    const existingContainer = document.getElementById('existingSalesContainer');
    
    if (tab === 'suggestions') {
        suggestionsTab.classList.add('active');
        existingTab.classList.remove('active');
        suggestionsContainer.style.display = 'block';
        existingContainer.style.display = 'none';
        loadSaleSuggestions();
    } else {
        existingTab.classList.add('active');
        suggestionsTab.classList.remove('active');
        existingContainer.style.display = 'block';
        suggestionsContainer.style.display = 'none';
        loadExistingSales();
    }
}

async function editSale(saleId) {
    // Load sale details and open edit modal
    try {
        const token = localStorage.getItem('hub_access_token');
        const response = await fetch(`${API_BASE}/api/sellers/sales`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        if (data.success && data.data) {
            const sale = data.data.find(s => s.id === saleId);
            if (sale) {
                openEditSaleModal(sale);
            }
        }
    } catch (error) {
        console.error('Error loading sale:', error);
        alert('Error loading sale details');
    }
}

function openEditSaleModal(sale) {
    // Create or show edit modal
    let modal = document.getElementById('editSaleModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'editSaleModal';
        modal.className = 'modal';
        modal.hidden = true;
        modal.innerHTML = `
            <div class="modal-overlay" onclick="closeEditSaleModal()"></div>
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h3>Edit Sale</h3>
                    <button class="modal-close" onclick="closeEditSaleModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <input type="hidden" id="editSaleId">
                    <div class="form-group">
                        <label>Product:</label>
                        <div id="editSaleProductName" style="padding: 8px; background: #f5f5f5; border-radius: 4px;"></div>
                    </div>
                    <div class="form-group">
                        <label>Current Price:</label>
                        <div id="editSaleCurrentPrice" style="padding: 8px; background: #f5f5f5; border-radius: 4px;"></div>
                    </div>
                    <div class="form-group">
                        <label>Discount Percentage (1-50%):</label>
                        <input type="number" id="editSaleDiscount" min="1" max="50" step="0.5" 
                               oninput="updateEditSalePreview()">
                    </div>
                    <div class="form-group">
                        <label>End Date (Optional):</label>
                        <input type="date" id="editSaleValidUntil">
                    </div>
                    <div class="sale-preview" id="editSalePreview"></div>
                    <div class="modal-actions">
                        <button class="btn-cancel" onclick="closeEditSaleModal()">Cancel</button>
                        <button class="btn-submit" onclick="saveEditSale()">Save Changes</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    document.getElementById('editSaleId').value = sale.id;
    document.getElementById('editSaleProductName').textContent = sale.product_title || 'Unknown Product';
    document.getElementById('editSaleCurrentPrice').textContent = `₱${parseFloat(sale.original_price || sale.current_price || 0).toFixed(2)}`;
    document.getElementById('editSaleDiscount').value = sale.discount_percentage || 0;
    document.getElementById('editSaleValidUntil').value = sale.valid_until ? sale.valid_until.split('T')[0] : '';
    
    updateEditSalePreview();
    modal.hidden = false;
}

function updateEditSalePreview() {
    const currentPrice = parseFloat(document.getElementById('editSaleCurrentPrice').textContent.replace('₱', '').replace(',', ''));
    const discount = parseFloat(document.getElementById('editSaleDiscount').value) || 0;
    const salePrice = currentPrice * (1 - discount / 100);
    const savings = currentPrice - salePrice;
    
    const preview = document.getElementById('editSalePreview');
    preview.innerHTML = `
        <h4>Preview:</h4>
        <div class="preview-row">
            <span>Sale Price:</span>
            <strong>₱${salePrice.toFixed(2)}</strong>
        </div>
        <div class="preview-row">
            <span>Customer Saves:</span>
            <strong>₱${savings.toFixed(2)} (${discount}%)</strong>
        </div>
    `;
}

function closeEditSaleModal() {
    const modal = document.getElementById('editSaleModal');
    if (modal) modal.hidden = true;
}

async function saveEditSale() {
    const saleId = document.getElementById('editSaleId').value;
    const discount = parseFloat(document.getElementById('editSaleDiscount').value);
    const validUntil = document.getElementById('editSaleValidUntil').value;
    
    if (!discount || discount < 1 || discount > 50) {
        alert('Please enter a valid discount between 1% and 50%');
        return;
    }
    
    try {
        const token = localStorage.getItem('hub_access_token');
        const response = await fetch(`${API_BASE}/api/sellers/sales/${saleId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                discount_percentage: discount,
                valid_until: validUntil || null,
                reason: 'expiring_soon'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (window.notify) {
                notify.success('Sale updated successfully!');
            } else {
                alert('Sale updated successfully!');
            }
            closeEditSaleModal();
            loadExistingSales();
        } else {
            if (window.notify) {
                notify.error(data.message || 'Failed to update sale');
            } else {
                alert(data.message || 'Failed to update sale');
            }
        }
    } catch (error) {
        console.error('Error updating sale:', error);
        alert('Error updating sale');
    }
}

async function deleteSale(saleId) {
    if (!confirm('Are you sure you want to remove this sale request?')) {
        return;
    }
    
    try {
        const token = localStorage.getItem('hub_access_token');
        const response = await fetch(`${API_BASE}/api/sellers/sales/${saleId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (window.notify) {
                notify.success('Sale removed successfully!');
            } else {
                alert('Sale removed successfully!');
            }
            loadExistingSales();
        } else {
            if (window.notify) {
                notify.error(data.message || 'Failed to remove sale');
            } else {
                alert(data.message || 'Failed to remove sale');
            }
        }
    } catch (error) {
        console.error('Error deleting sale:', error);
        alert('Error removing sale');
    }
}

// Expose functions globally
window.switchSalesTab = switchSalesTab;
window.editSale = editSale;
window.deleteSale = deleteSale;
window.closeEditSaleModal = closeEditSaleModal;
window.updateEditSalePreview = updateEditSalePreview;
window.saveEditSale = saveEditSale;

// Auto-load on page load if on seller dashboard
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('seller_dashboard')) {
        loadSaleSuggestions();
    }
});
