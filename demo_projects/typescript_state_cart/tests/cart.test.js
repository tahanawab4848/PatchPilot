const { calculateSubtotal, applyDiscount, calculateCartTotal } = require('../src/cart');

describe('ShoppingCart Pricing & Discounts', () => {
  test('calculateSubtotal sums up item prices multiplied by quantities', () => {
    const items = [
      { id: 'item-1', price: 20.0, quantity: 2 },
      { id: 'item-2', price: 15.0, quantity: 1 },
    ];
    expect(calculateSubtotal(items)).toBe(55.0);
  });

  test('applyDiscount should not mutate original cart items', () => {
    const originalItems = [
      { id: 'item-1', price: 100.0, quantity: 1 },
      { id: 'item-2', price: 50.0, quantity: 2 },
    ];
    const cart = {
      id: 'cart-123',
      items: originalItems,
    };

    const discountedCart = applyDiscount(cart, 20); // 20% off
    expect(discountedCart.total).toBe(160.0); // (80*1) + (40*2) = 160

    // Original items must NOT be mutated in-place
    expect(originalItems[0].price).toBe(100.0);
    expect(originalItems[1].price).toBe(50.0);
  });

  test('calculateCartTotal maintains idempotency across multiple discount evaluations', () => {
    const cart = {
      id: 'cart-999',
      items: [
        { id: 'item-1', price: 100.0, quantity: 1 },
      ],
    };

    const discountA = applyDiscount(cart, 10); // 10% off -> 90.0
    expect(discountA.total).toBe(90.0);

    const discountB = applyDiscount(cart, 10); // 10% off original -> should still be 90.0, NOT 81.0!
    expect(discountB.total).toBe(90.0);
  });

  test('calculateCartTotal computes correct 8% tax rate', () => {
    const cart = {
      items: [{ id: 'item-1', price: 50.0, quantity: 2 }],
    };
    const totals = calculateCartTotal(cart);
    expect(totals.subtotal).toBe(100.0);
    expect(totals.tax).toBe(8.0);
    expect(totals.grandTotal).toBe(108.0);
  });
});
