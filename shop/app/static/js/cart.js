/**
 * Shopping Cart Management
 */

async function addToCart(productId, quantity = 1) {
    try {
        const response = await fetch('/api/cart/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_id: parseInt(productId),
                quantity: parseInt(quantity)
            }),
        });

        if (response.ok) {
            const data = await response.json();
            // Update cart badge
            const badge = document.getElementById('cart-badge');
            if (badge) {
                badge.textContent = data.item_count;
            }
            if (typeof showToast === 'function') {
                showToast('Item added to bag successfully!', 'Success', 'success');
            }
        } else {
            const error = await response.json();
            if (typeof showToast === 'function') {
                showToast(error.detail || 'Failed to add item', 'Error', 'danger');
            }
        }
    } catch (err) {
        console.error('Cart error:', err);
        if (typeof showToast === 'function') {
            showToast('Something went wrong. Please try again.', 'Error', 'danger');
        }
    }
}

async function updateCart(productId, quantity) {
    if (quantity < 1) {
        return removeFromCart(productId);
    }

    try {
        const response = await fetch('/api/cart/update', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_id: parseInt(productId),
                quantity: parseInt(quantity)
            }),
        });

        if (response.ok) {
            location.reload(); // Refresh to update totals
        } else {
            const error = await response.json();
            if (typeof showToast === 'function') {
                showToast(error.detail || 'Failed to update quantity', 'Error', 'danger');
            }
        }
    } catch (err) {
        console.error('Cart error:', err);
    }
}

async function removeFromCart(productId) {
    try {
        const response = await fetch(`/api/cart/remove/${productId}`, {
            method: 'DELETE',
        });

        if (response.ok) {
            location.reload();
        } else {
            if (typeof showToast === 'function') {
                showToast('Failed to remove item', 'Error', 'danger');
            }
        }
    } catch (err) {
        console.error('Cart error:', err);
    }
}
