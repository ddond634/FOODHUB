#!/usr/bin/env python3
"""Add sync function calls to shop.html"""

# Read file
with open('frontend/shop.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add sync calls after cart success (note: 6 tabs before notify)
old1 = """\t\t\t\t\t\tnotify.success(`Added ${qty} item(s) to cart!`);
\t\t\t\t\t\tcloseModal();"""

new1 = """\t\t\t\t\t\tnotify.success(`Added ${qty} item(s) to cart!`);
\t\t\t\t\t\t// Sync cart badge and dropdown
\t\t\t\t\t\tif (window.syncCartBadge) window.syncCartBadge();
\t\t\t\t\t\tif (window.syncCartDropdown) window.syncCartDropdown();
\t\t\t\t\t\tcloseModal();"""

if old1 in content:
    content = content.replace(old1, new1)
    print('✅ Cart sync added')
else:
    print('❌ Cart pattern not found')

# Add sync calls after wishlist success (note: 7 tabs before notify)
old2 = """\t\t\t\t\t\t\tnotify.success('Added to wishlist!');
\t\t\t\t\t\t\tbtn.innerHTML = '<i class="fa fa-heart" style="color: #e74c3c;"></i> In Wishlist';"""

new2 = """\t\t\t\t\t\t\tnotify.success('Added to wishlist!');
\t\t\t\t\t\t\t// Sync wishlist badge and dropdown
\t\t\t\t\t\t\tif (window.syncWishlistBadge) window.syncWishlistBadge();
\t\t\t\t\t\t\tif (window.syncWishlistDropdown) window.syncWishlistDropdown();
\t\t\t\t\t\t\tbtn.innerHTML = '<i class="fa fa-heart" style="color: #e74c3c;"></i> In Wishlist';"""

if old2 in content:
    content = content.replace(old2, new2)
    print('✅ Wishlist sync added')
else:
    print('❌ Wishlist pattern not found')

# Write file
with open('frontend/shop.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ shop.html updated')
