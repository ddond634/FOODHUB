// Copy and paste this into your browser console while on the admin dashboard

async function createAndVerifyTestAccounts() {
    console.log('🔧 Creating test accounts...');
    
    try {
        // Step 1: Create accounts
        const createResponse = await fetch('/api/admin/create-test-accounts', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        const createData = await createResponse.json();
        console.log('📝 Create response:', createData);
        
        if (!createData.success) {
            console.error('❌ Failed to create accounts:', createData);
            return;
        }
        
        // Step 2: Verify accounts exist
        const verifyResponse = await fetch('/api/admin/verify-test-accounts', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('hub_access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        const verifyData = await verifyResponse.json();
        console.log('✅ Verification:', verifyData);
        
        // Step 3: Refresh the dashboard
        console.log('🔄 Refreshing dashboard...');
        if (typeof loadSellersData === 'function') {
            await loadSellersData();
        }
        if (typeof loadRidersData === 'function') {
            await loadRidersData();
        }
        
        console.log('✨ Done! Check your seller and rider tabs.');
        
        return {
            created: createData,
            verified: verifyData
        };
    } catch (error) {
        console.error('❌ Error:', error);
        return null;
    }
}

// Run it
createAndVerifyTestAccounts();

