import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import 'cart_screen.dart';
import 'home_screen.dart';
import 'profile_screen.dart';
import 'rider_dashboard_screen.dart';
import 'rider_deliveries_screen.dart';
import 'seller_dashboard_screen.dart';
import 'seller_inventory_screen.dart';
import 'shop_screen.dart';

class RoleShellScreen extends StatelessWidget {
  const RoleShellScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AppState>().userRole;
    if (role == 'seller') return const _SellerShell();
    if (role == 'rider') return const _RiderShell();
    return const BuyerShellScreen();
  }
}

class BuyerShellScreen extends StatefulWidget {
  const BuyerShellScreen({super.key});

  @override
  State<BuyerShellScreen> createState() => _BuyerShellScreenState();
}

class _BuyerShellScreenState extends State<BuyerShellScreen> {
  int _index = 0;

  static const _screens = [HomeScreen(), ShopScreen(), CartScreen(), ProfileScreen()];

  @override
  Widget build(BuildContext context) {
    final cartCount = context.watch<AppState>().cartCount;
    return Scaffold(
      body: IndexedStack(index: _index, children: _screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          const NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          const NavigationDestination(icon: Icon(Icons.store_outlined), selectedIcon: Icon(Icons.store), label: 'Shop'),
          NavigationDestination(
            icon: Badge(isLabelVisible: cartCount > 0, label: Text('$cartCount'), child: const Icon(Icons.shopping_cart_outlined)),
            selectedIcon: Badge(isLabelVisible: cartCount > 0, label: Text('$cartCount'), child: const Icon(Icons.shopping_cart)),
            label: 'Cart',
          ),
          const NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}

class _SellerShell extends StatefulWidget {
  const _SellerShell();

  @override
  State<_SellerShell> createState() => _SellerShellState();
}

class _SellerShellState extends State<_SellerShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    const screens = [SellerDashboardScreen(), SellerInventoryScreen(), ProfileScreen()];
    return Scaffold(
      body: IndexedStack(index: _index, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.analytics_outlined), selectedIcon: Icon(Icons.analytics), label: 'Analytics'),
          NavigationDestination(icon: Icon(Icons.inventory_2_outlined), selectedIcon: Icon(Icons.inventory_2), label: 'Products'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}

class _RiderShell extends StatefulWidget {
  const _RiderShell();

  @override
  State<_RiderShell> createState() => _RiderShellState();
}

class _RiderShellState extends State<_RiderShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    const screens = [RiderDashboardScreen(), RiderDeliveriesScreen(), ProfileScreen()];
    return Scaffold(
      body: IndexedStack(index: _index, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.analytics_outlined), selectedIcon: Icon(Icons.analytics), label: 'Analytics'),
          NavigationDestination(icon: Icon(Icons.delivery_dining_outlined), selectedIcon: Icon(Icons.delivery_dining), label: 'Deliveries'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}
