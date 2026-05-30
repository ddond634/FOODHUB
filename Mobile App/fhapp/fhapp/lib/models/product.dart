class Product {
  final int id;
  final String title;
  final String description;
  final double price;
  final int stock;
  final int? sellerId;
  final String? category;
  final String? categoryNormalized;
  final String? imgUrl;
  final List<String> imageUrls;
  final String? sellerBusinessName;
  final String? sellerStoreName;
  final String? sellerFirstName;
  final String? sellerLastName;
  final double averageRating;
  final int reviewCount;

  const Product({
    required this.id,
    required this.title,
    required this.description,
    required this.price,
    required this.stock,
    this.sellerId,
    this.category,
    this.categoryNormalized,
    this.imgUrl,
    this.imageUrls = const [],
    this.sellerBusinessName,
    this.sellerStoreName,
    this.sellerFirstName,
    this.sellerLastName,
    this.averageRating = 0,
    this.reviewCount = 0,
  });

  String get sellerDisplayName =>
      (sellerStoreName?.isNotEmpty == true
              ? sellerStoreName
              : sellerBusinessName?.isNotEmpty == true
                  ? sellerBusinessName
                  : null) ??
      'Unknown Seller';

  factory Product.fromJson(Map<String, dynamic> json) {
    final imageUrlsRaw = json['image_urls'];
    final imageUrls = imageUrlsRaw is List
        ? imageUrlsRaw.map((e) => e.toString()).where((e) => e.isNotEmpty).toList()
        : <String>[];

    return Product(
      id: (json['id'] as num).toInt(),
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      price: (json['price'] is num) ? (json['price'] as num).toDouble() : double.tryParse('${json['price']}') ?? 0,
      stock: (json['stock'] as num?)?.toInt() ?? 0,
      sellerId: (json['seller_id'] as num?)?.toInt(),
      category: json['category']?.toString(),
      categoryNormalized: json['category_normalized']?.toString(),
      imgUrl: json['img_url']?.toString(),
      imageUrls: imageUrls,
      sellerBusinessName: json['seller_business_name']?.toString(),
      sellerStoreName: json['seller_store_name']?.toString(),
      sellerFirstName: json['seller_first_name']?.toString(),
      sellerLastName: json['seller_last_name']?.toString(),
      averageRating: (json['average_rating'] as num?)?.toDouble() ?? 0,
      reviewCount: (json['review_count'] as num?)?.toInt() ?? 0,
    );
  }
}
