class SellerShop {
  final int sellerId;
  final int userId;
  final String displayName;
  final String businessName;
  final String? category;
  final String? fullAddress;
  final String? storeLogo;
  final int totalProducts;

  const SellerShop({
    required this.sellerId,
    required this.userId,
    required this.displayName,
    required this.businessName,
    this.category,
    this.fullAddress,
    this.storeLogo,
    this.totalProducts = 0,
  });

  factory SellerShop.fromJson(Map<String, dynamic> json) {
    final businessName = json['business_name']?.toString() ??
        json['store_name']?.toString() ??
        json['display_name']?.toString() ??
        'Store';

    return SellerShop(
      sellerId: (json['seller_id'] as num?)?.toInt() ?? (json['id'] as num?)?.toInt() ?? 0,
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      displayName: json['display_name']?.toString() ?? businessName,
      businessName: businessName,
      category: json['category']?.toString(),
      fullAddress: json['full_address']?.toString(),
      storeLogo: json['store_logo']?.toString(),
      totalProducts: (json['total_products'] as num?)?.toInt() ?? 0,
    );
  }
}

class SellerProfile {
  final int id;
  final int userId;
  final String businessName;
  final String storeName;
  final String? storeDescription;
  final String? storeLogo;
  final String? category;
  final String? city;
  final String? province;
  final String? region;
  final String? fullAddress;

  const SellerProfile({
    required this.id,
    required this.userId,
    required this.businessName,
    required this.storeName,
    this.storeDescription,
    this.storeLogo,
    this.category,
    this.city,
    this.province,
    this.region,
    this.fullAddress,
  });

  String get displayName => storeName.isNotEmpty ? storeName : businessName;

  factory SellerProfile.fromJson(Map<String, dynamic> json) {
    final businessName = json['business_name']?.toString() ?? 'Store';
    final storeName = json['store_name']?.toString() ?? businessName;

    return SellerProfile(
      id: (json['id'] as num?)?.toInt() ?? 0,
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      businessName: businessName,
      storeName: storeName,
      storeDescription: json['store_description']?.toString(),
      storeLogo: json['store_logo']?.toString(),
      category: json['category']?.toString(),
      city: json['city']?.toString(),
      province: json['province']?.toString(),
      region: json['region']?.toString(),
      fullAddress: json['full_address']?.toString(),
    );
  }
}
