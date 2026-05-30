import 'package:flutter/foundation.dart';
import '../models/cart_item.dart';
import '../models/hub_user.dart';
import '../models/product.dart';
import '../models/seller.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/cart_service.dart';
import '../services/product_service.dart';
import '../services/seller_service.dart';

class AppState extends ChangeNotifier {
  AppState() {
    _apiClient = ApiClient();
    _productService = ProductService(_apiClient);
    _cartService = CartService(_apiClient);
    _sellerService = SellerService(_apiClient);
  }

  final AuthService auth = AuthService();
  late final ApiClient _apiClient;
  late final ProductService _productService;
  late final CartService _cartService;
  late final SellerService _sellerService;

  bool _loading = true;
  bool _busy = false;
  String? _error;

  List<Product> _products = [];
  List<Product> _bestSellers = [];
  List<SellerShop> _shops = [];
  List<CartItem> _cartItems = [];
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
  List<String> get categories => _categories;
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
      await Future.wait([
        refreshProducts(),
        refreshBestSellers(),
        refreshShops(),
        if (auth.isLoggedIn) refreshCart(),
      ]);
      _categories = await _productService.fetchCategories();
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
      await refreshCart();
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
      await refreshCart();
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
