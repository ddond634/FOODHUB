class Product {
  final int id;
  final String title;
  final String description;
  final double price;
  final int stock;
  final int? sellerId;
  final String? category;
  final String? imgUrl;

  const Product({
    required this.id,
    required this.title,
    required this.description,
    required this.price,
    required this.stock,
    this.sellerId,
    this.category,
    this.imgUrl,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as int,
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      price: (json['price'] is num) ? (json['price'] as num).toDouble() : double.tryParse('${json['price']}') ?? 0,
      stock: (json['stock'] as num?)?.toInt() ?? 0,
      sellerId: (json['seller_id'] as num?)?.toInt(),
      category: json['category']?.toString(),
      imgUrl: json['img_url']?.toString(),
    );
  }
}
