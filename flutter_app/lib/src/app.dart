import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth/auth_repository.dart';
import 'auth/models.dart';
import 'features/chat/chat_api_client.dart';
import 'features/expenses/expense_api_client.dart';
import 'network/authed_dio.dart';

class ExpenseTrackerApp extends ConsumerStatefulWidget {
  const ExpenseTrackerApp({super.key});

  @override
  ConsumerState<ExpenseTrackerApp> createState() => _ExpenseTrackerAppState();
}

class _ExpenseTrackerAppState extends ConsumerState<ExpenseTrackerApp> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(authRepositoryProvider.notifier).bootstrap());
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authRepositoryProvider);
    return MaterialApp(
      title: 'Expense Tracker',
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.blue),
      home: authState.isAuthenticated ? const HomeScreen() : const AuthScreen(),
    );
  }
}

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  bool _isSignUp = false;
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final notifier = ref.read(authRepositoryProvider.notifier);
    if (_isSignUp) {
      await notifier.signUp(
        RegisterPayload(
          username: _usernameController.text.trim(),
          email: _emailController.text.trim(),
          password: _passwordController.text,
        ),
      );
      return;
    }
    await notifier.signIn(
      LoginPayload(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authRepositoryProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(_isSignUp ? 'Create account' : 'Sign in'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_isSignUp)
              TextField(
                controller: _usernameController,
                decoration: const InputDecoration(labelText: 'Username'),
              ),
            TextField(
              controller: _emailController,
              decoration: const InputDecoration(labelText: 'Email'),
              keyboardType: TextInputType.emailAddress,
            ),
            TextField(
              controller: _passwordController,
              decoration: const InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
            const SizedBox(height: 12),
            if (authState.errorMessage != null)
              Text(
                authState.errorMessage!,
                style: const TextStyle(color: Colors.red),
              ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: authState.isLoading ? null : _submit,
              child: Text(authState.isLoading
                  ? 'Please wait...'
                  : (_isSignUp ? 'Sign up' : 'Sign in')),
            ),
            TextButton(
              onPressed: authState.isLoading
                  ? null
                  : () => setState(() => _isSignUp = !_isSignUp),
              child: Text(_isSignUp
                  ? 'Already have an account? Sign in'
                  : 'Need an account? Sign up'),
            ),
          ],
        ),
      ),
    );
  }
}

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  late final ExpenseApiClient _expenseClient;
  late final ChatApiClient _chatClient;
  final _chatController = TextEditingController();
  final _amountController = TextEditingController();
  final _descriptionController = TextEditingController();
  String _chatOutput = '';
  List<Map<String, dynamic>> _expenses = const [];

  @override
  void initState() {
    super.initState();
    final dio = ref.read(authedDioProvider);
    _expenseClient = ExpenseApiClient(dio);
    _chatClient = ChatApiClient(dio);
    Future.microtask(_loadExpenses);
  }

  @override
  void dispose() {
    _chatController.dispose();
    _amountController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _loadExpenses() async {
    final items = await _expenseClient.listExpenses();
    if (mounted) {
      setState(() => _expenses = items);
    }
  }

  Future<void> _addExpense() async {
    final amount = double.tryParse(_amountController.text.trim());
    if (amount == null) return;
    await _expenseClient.addExpense(
      amount: amount,
      date: DateTime.now(),
      description: _descriptionController.text.trim().isEmpty
          ? null
          : _descriptionController.text.trim(),
    );
    _amountController.clear();
    _descriptionController.clear();
    await _loadExpenses();
  }

  Future<void> _sendChat() async {
    final text = _chatController.text.trim();
    if (text.isEmpty) return;
    final response = await _chatClient.chat(text: text);
    setState(() => _chatOutput = response.toString());
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authRepositoryProvider).user;
    return Scaffold(
      appBar: AppBar(
        title: Text('Hello ${user?.username ?? ''}'),
        actions: [
          IconButton(
            onPressed: () => ref.read(authRepositoryProvider.notifier).signOut(),
            icon: const Icon(Icons.logout),
          )
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Add expense'),
          TextField(
            controller: _amountController,
            decoration: const InputDecoration(labelText: 'Amount'),
            keyboardType: TextInputType.number,
          ),
          TextField(
            controller: _descriptionController,
            decoration: const InputDecoration(labelText: 'Description'),
          ),
          FilledButton(onPressed: _addExpense, child: const Text('Save expense')),
          const SizedBox(height: 16),
          const Text('Your expenses'),
          ..._expenses.map((item) => ListTile(
                title: Text('\$${item['amount']}'),
                subtitle: Text(item['description']?.toString() ?? ''),
              )),
          const Divider(),
          const Text('Chat with agent'),
          TextField(
            controller: _chatController,
            decoration: const InputDecoration(labelText: 'Message'),
          ),
          FilledButton(onPressed: _sendChat, child: const Text('Send')),
          if (_chatOutput.isNotEmpty) Text(_chatOutput),
        ],
      ),
    );
  }
}
