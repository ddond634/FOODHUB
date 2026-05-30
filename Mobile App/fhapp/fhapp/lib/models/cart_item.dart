class CartItem {
  final int cartId;
  final int productId;
  final int? variationId;
  final int quantity;
  final String title;
  final String imgUrl;
  final String? variation;
  final double unitPrice;
  final double totalPrice;

  const CartItem({
    required this.cartId,
    required this.productId,
    this.variationId,
    required this.quantity,
    required this.title,
    required this.imgUrl,
    this.variation,
    required this.unitPrice,
    required this.totalPrice,
  });

  factory CartItem.fromJson(Map<String, dynamic> json) {
    return CartItem(
      cartId: (json['cart_id'] as num).toInt(),
      productId: (json['product_id'] as num).toInt(),
      variationId: (json['variation_id'] as num?)?.toInt(),
      quantity: (json['quantity'] as num?)?.toInt() ?? 1,
      title: json['title']?.toString() ?? '',
      imgUrl: json['img_url']?.toString() ?? '',
      variation: json['variation']?.toString(),
      unitPrice: (json['unit_price'] as num?)?.toDouble() ?? 0,
      totalPrice: (json['total_price'] as num?)?.toDouble() ?? 0,
    );
  }
}
