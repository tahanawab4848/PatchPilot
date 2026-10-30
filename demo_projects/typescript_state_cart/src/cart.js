/**
 * Shopping Cart calculation utilities.
 */

function calculateSubtotal(items) {
  return items.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

function applyDiscount(cart, discountPercent) {
  if (discountPercent <= 0 || discountPercent > 100) {
    return cart;
  }

  // DEFECT: Mutates cart.items in-place instead of creating an immutable copy
  cart.items.forEach(item => {
    item.price = Math.round(item.price * (1 - discountPercent / 100) * 100) / 100;
  });

  cart.discountPercent = discountPercent;
  cart.total = calculateSubtotal(cart.items);
  return cart;
}

function calculateCartTotal(cart) {
  const subtotal = calculateSubtotal(cart.items);
  const tax = Math.round(subtotal * 0.08 * 100) / 100;
  return {
    subtotal,
    tax,
    grandTotal: subtotal + tax,
  };
}

module.exports = {
  calculateSubtotal,
  applyDiscount,
  calculateCartTotal,
};
