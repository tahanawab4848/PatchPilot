# TypeScript / Node.js Shopping Cart Service

Polyglot enterprise checkout and state management service for asynchronous e-commerce order processing.

## Known Defect
In `src/cart.js`, the promotion calculation function `applyDiscount(cart, discountPercent)` mutates the shared `cart.items` array in-place instead of creating an immutable cloned structure:
```javascript
cart.items.forEach(item => {
  item.price = item.price * (1 - discountPercent / 100);
});
return cart;
```
Because the cart items are mutated in-place:
- Consecutive or concurrent discount calculations compound the discounts unintentionally (e.g., a 10% coupon applied twice reduces $100 to $90 then to $81 instead of computing independent pricing tiers).
- The original catalog price reference on `cart.items` is permanently corrupted.

Failing tests:
- `tests/cart.test.js::applyDiscount should not mutate original cart items`
- `tests/cart.test.js::calculateCartTotal maintains idempotency across multiple discount evaluations`
