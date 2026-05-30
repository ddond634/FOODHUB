import 'package:flutter/foundation.dart';
import '../models/cart_item.dart';
import '../models/earnings.dart';
import '../models/hub_user.dart';
import '../models/order.dart';
import '../models/product.dart';
import '../models/seller.dart';
import '../widgets/checkout_form_dialog.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/cart_service.dart';
import '../services/order_service.dart';
import '../services/product_service.dart';
import '../services/rider_service.dart';
import '../services/seller_product_service.dart';
import '../services/seller_service.dart';

class AppState extends ChangeNotifier {
  AppState() {
    _apiClient = ApiClient();
    _productService = ProductService(_apiClient);
    _cartService = CartService(_apiClient);
    _sellerService = SellerService(_apiClient);
    _orderService = OrderService(_apiClient);
    _sellerProductService = SellerProductService(_apiClient);
    _riderService = RiderService(_apiClient);
  }

  final AuthService auth = AuthService();
  late final ApiClient _apiClient;
  late final ProductService _productService;
  late final CartService _cartService;
  late final SellerService _sellerService;
  late final OrderService _orderService;
  late final SellerProductService _sellerProductService;
  late final RiderService _riderService;

  bool _loading = true;
  bool _busy = false;
  String? _error;

  List<Product> _products = [];
  List<Product> _bestSellers = [];
  List<SellerShop> _shops = [];
  List<CartItem> _cartItems = [];
  List<Product> _sellerProducts = [];
  List<HubOrder> _availableRiderOrders = [];
  List<HubOrder> _assignedRiderOrders = [];
  SellerDashboardStats? _sellerDashboard;
  SellerEarningsSummary? _sellerEarnings;
  RiderDashboardStats? _riderDashboard;
  List<String> _categories = [];
  String? _selectedCategory;
  String _searchQuery = '';

  bool get loading => _loading;
  bool get busy => _busy;
  String? get error => _error;
  HubUser? get user => auth.user;
  bool get isLoggedIn => auth.isLoggedIn;
  List<Product> get products => _products;
  List<Product> get bestSellers => _bestSellers;
  List<SellerShop> get shops => _shops;
  List<CartItem> get cartItems => _cartItems;
  List<Product> get sellerProducts => _sellerProducts;
  List<HubOrder> get availableRiderOrders => _availableRiderOrders;
  List<HubOrder> get assignedRiderOrders => _assignedRiderOrders;
  SellerDashboardStats? get sellerDashboard => _sellerDashboard;
  SellerEarningsSummary? get sellerEarnings => _sellerEarnings;
  RiderDashboardStats? get riderDashboard => _riderDashboard;
  List<String> get categories => _categories;
  String get userRole => user?.role ?? 'customer';
  bool get isBuyer => userRole == 'customer' || userRole == 'buyer';
  bool get isSeller => userRole == 'seller';
  bool get isRider => userRole == 'rider';
  String? get selectedCategory => _selectedCategory;
  String get searchQuery => _searchQuery;

  int get cartCount => _cartItems.fold(0, (sum, item) => sum + item.quantity);
  double get cartTotal => _cartItems.fold(0, (sum, item) => sum + item.totalPrice);

  Future<void> bootstrap() async {
    _loading = true;
    notifyListeners();
    try {
      await auth.loadSession();
      _syncToken();
      if (isBuyer) {
        await Future.wait([
          refreshProducts(),
          refreshBestSellers(),
          refreshShops(),
          if (auth.isLoggedIn) refreshCart(),
        ]);
        _categories = await _productService.fetchCategories();
      } else if (isSeller) {
        await Future.wait([
          refreshSellerProducts(),
          refreshSellerEarnings(),
        ]);
      } else if (isRider) {
        await refreshRiderOrders();
      }
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void _syncToken() {
    _apiClient.hubToken = auth.token;
  }

  Future<void> login(String email, String password) async {
    await _runBusy(() async {
      await auth.login(email, password);
      _syncToken();
      if (isBuyer) {
        await refreshCart();
      } else if (isSeller) {
        await refreshSellerProducts();
        await refreshSellerEarnings();
      } else if (isRider) {
        await refreshRiderOrders();
      }
    });
  }

  Future<void> register({
    required String email,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    await _runBusy(() async {
      await auth.register(
        email: email,
        password: password,
        firstName: firstName,
        lastName: lastName,
      );
      _syncToken();
      if (isBuyer) {
        await refreshCart();
      }
    });
  }

  Future<void> logout() async {
    await auth.logout();
    _syncToken();
    _cartItems = [];
    notifyListeners();
  }

  Future<void> refreshProducts() async {
    _products = await _productService.fetchProducts(
      category: _selectedCategory,
      query: _searchQuery.isEmpty ? null : _searchQuery,
    );
    notifyListeners();
  }

  Future<void> refreshBestSellers() async {
    _bestSellers = await _productService.fetchBestSellers();
    notifyListeners();
  }

  Future<void> refreshShops() async {
    _shops = await _sellerService.fetchActiveShops();
    notifyListeners();
  }

  Future<void> refreshCart() async {
    if (!auth.isLoggedIn) {
      _cartItems = [];
      notifyListeners();
      return;
    }
    _cartItems = await _cartService.fetchCart();
    notifyListeners();
  }

  Future<void> setCategory(String? category) async {
    _selectedCategory = category;
    await refreshProducts();
  }

  Future<void> setSearchQuery(String query) async {
    _searchQuery = query;
    await refreshProducts();
  }

  Future<void> addToCart(int productId) async {
    if (!isBuyer) {
      throw Exception('Only buyers can add items to cart');
    }
    if (!auth.isLoggedIn) {
      throw Exception('Please sign in to add items to your cart');
    }
    await _runBusy(() async {
      await _cartService.addToCart(productId);
      await refreshCart();
    });
  }

  Future<void> updateCartQuantity(int cartId, int quantity) async {
    await _runBusy(() async {
      if (quantity < 1) {
        await _cartService.removeItem(cartId);
      } else {
        await _cartService.updateQuantity(cartId, quantity);
      }
      await refreshCart();
    });
  }

  Future<void> removeFromCart(int cartId) async {
    await _runBusy(() async {
      await _cartService.removeItem(cartId);
      await refreshCart();
    });
  }

  Future<int> checkout({
    required String payment,
    required CheckoutFormData buyerInfo,
  }) async {
    if (!isBuyer) {
      throw Exception('Only buyers can checkout');
    }
    if (!auth.isLoggedIn || _cartItems.isEmpty) {
      throw Exception('Cart is empty');
    }
    final delivery = 50.0;
    final subtotal = cartTotal;
    final total = subtotal + delivery;
    final items = _cartItems.map((item) => {
      'product_id': item.productId,
      'quantity': item.quantity,
      'price': item.unitPrice,
      'title': item.title,
    }).toList();

    _busy = true;
    _error = null;
    notifyListeners();
    try {
      final orderId = await _orderService.checkout(
        items: items,
        customer: buyerInfo.toCustomerPayload(),
        delivery: delivery,
        subtotal: subtotal,
        total: total,
        payment: payment,
      );
      await refreshCart();
      return orderId;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      rethrow;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  Future<void> refreshSellerProducts() async {
    _sellerProducts = await _sellerProductService.fetchMyProducts();
    notifyListeners();
  }

  Future<void> refreshSellerEarnings() async {
    _sellerDashboard = await _sellerService.fetchDashboard();
    _sellerEarnings = await _sellerService.fetchEarningsSummary();
    notifyListeners();
  }

  Future<void> createSellerProduct({
    required String title,
    required String description,
    required double price,
    required int stock,
    String category = 'General',
  }) async {
    await _runBusy(() async {
      await _sellerProductService.createProduct(
        title: title,
        description: description,
        price: price,
        stock: stock,
        category: category,
      );
      await refreshSellerProducts();
    });
  }

  Future<void> updateSellerProduct(int id, Map<String, dynamic> updates) async {
    await _runBusy(() async {
      await _sellerProductService.updateProduct(id, updates);
      await refreshSellerProducts();
    });
  }

  Future<void> restockSellerProduct(int id, int stock) async {
    await updateSellerProduct(id, {'stock': stock});
  }

  Future<void> deleteSellerProduct(int id) async {
    await _runBusy(() async {
      await _sellerProductService.deleteProduct(id);
      await refreshSellerProducts();
    });
  }

  Future<void> refreshRiderOrders() async {
    _availableRiderOrders = await _riderService.fetchAvailableOrders();
    _assignedRiderOrders = await _riderService.fetchMyOrders();
    try {
      _riderDashboard = await _riderService.fetchDashboard();
    } catch (_) {}
    notifyListeners();
  }

  Future<void> acceptRiderOrder(int orderId) async {
    await _runBusy(() async {
      await _riderService.acceptOrder(orderId);
      await refreshRiderOrders();
    });
  }

  Future<void> updateRiderDelivery(int orderId, String status) async {
    await _runBusy(() async {
      await _riderService.updateDeliveryStatus(orderId, status);
      await refreshRiderOrders();
    });
  }

  Future<void> _runBusy(Future<void> Function() action) async {
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      await action();
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      rethrow;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }
}
