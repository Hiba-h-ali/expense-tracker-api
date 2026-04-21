import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

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
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.blue,
        scaffoldBackgroundColor: const Color(0xFFF5F7FB),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
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
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Card(
                elevation: 1,
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        _isSignUp ? 'Create your account' : 'Welcome back',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        _isSignUp
                            ? 'Sign up to start tracking your expenses.'
                            : 'Sign in to continue.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.black54,
                            ),
                      ),
                      const SizedBox(height: 20),
                      if (_isSignUp)
                        TextField(
                          controller: _usernameController,
                          decoration: const InputDecoration(labelText: 'Username'),
                        ),
                      if (_isSignUp) const SizedBox(height: 12),
                      TextField(
                        controller: _emailController,
                        decoration: const InputDecoration(labelText: 'Email'),
                        keyboardType: TextInputType.emailAddress,
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _passwordController,
                        decoration: const InputDecoration(labelText: 'Password'),
                        obscureText: true,
                      ),
                      const SizedBox(height: 12),
                      if (authState.errorMessage != null)
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            authState.errorMessage!,
                            style: TextStyle(color: Colors.red.shade700),
                          ),
                        ),
                      if (authState.errorMessage != null) const SizedBox(height: 12),
                      FilledButton(
                        onPressed: authState.isLoading ? null : _submit,
                        child: Text(authState.isLoading
                            ? 'Please wait...'
                            : (_isSignUp ? 'Sign up' : 'Sign in')),
                      ),
                      const SizedBox(height: 4),
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
              ),
            ),
          ),
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
  String? _chatSessionId;
  int? _selectedCategoryId;
  List<Map<String, dynamic>> _expenses = const [];
  List<Map<String, dynamic>> _categories = const [];

  @override
  void initState() {
    super.initState();
    final dio = ref.read(authedDioProvider);
    _expenseClient = ExpenseApiClient(dio);
    _chatClient = ChatApiClient(dio);
    Future.microtask(() async {
      await _loadCategories();
      await _loadExpenses();
      await _loadChatSession();
    });
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

  Future<void> _loadCategories() async {
    final items = await _expenseClient.listCategories();
    if (mounted) {
      setState(() => _categories = items);
    }
  }

  Future<void> _addExpense() async {
    final amount = double.tryParse(_amountController.text.trim());
    if (amount == null) return;
    await _expenseClient.addExpense(
      amount: amount,
      date: DateTime.now(),
      categoryId: _selectedCategoryId,
      description: _descriptionController.text.trim().isEmpty
          ? null
          : _descriptionController.text.trim(),
    );
    _amountController.clear();
    _descriptionController.clear();
    _selectedCategoryId = null;
    await _loadExpenses();
  }

  String _categoryNameForId(int? categoryId) {
    if (categoryId == null) return 'uncategorized';
    final category = _categories.firstWhere(
      (item) => item['id'] == categoryId,
      orElse: () => const {},
    );
    return category['name']?.toString() ?? 'category #$categoryId';
  }

  Future<void> _showEditExpenseDialog(Map<String, dynamic> item) async {
    final amountController =
        TextEditingController(text: (item['amount'] as num?)?.toString() ?? '');
    final descriptionController =
        TextEditingController(text: item['description']?.toString() ?? '');
    int? selectedCategoryId = item['category_id'] as int?;

    await showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Edit expense'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: amountController,
                decoration: const InputDecoration(labelText: 'Amount'),
                keyboardType: TextInputType.number,
              ),
              TextField(
                controller: descriptionController,
                decoration: const InputDecoration(labelText: 'Description'),
              ),
              DropdownButtonFormField<int?>(
                initialValue: selectedCategoryId,
                decoration: const InputDecoration(labelText: 'Category (optional)'),
                items: [
                  const DropdownMenuItem<int?>(
                    value: null,
                    child: Text('Auto categorize'),
                  ),
                  ..._categories.map(
                    (category) => DropdownMenuItem<int?>(
                      value: category['id'] as int,
                      child: Text(category['name']?.toString() ?? ''),
                    ),
                  ),
                ],
                onChanged: (value) => selectedCategoryId = value,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () async {
                final amount = double.tryParse(amountController.text.trim());
                if (amount == null) return;
                await _expenseClient.updateExpense(
                  expenseId: item['id'] as int,
                  amount: amount,
                  description: descriptionController.text.trim().isEmpty
                      ? null
                      : descriptionController.text.trim(),
                  categoryId: selectedCategoryId,
                );
                if (context.mounted) {
                  Navigator.of(context).pop();
                }
                await _loadExpenses();
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );

    amountController.dispose();
    descriptionController.dispose();
  }

  Future<void> _sendChat() async {
    final text = _chatController.text.trim();
    if (text.isEmpty) return;
    try {
      final response = await _chatClient.chat(
        text: text,
        sessionId: _chatSessionId,
      );
      final responseSessionId = response['session_id']?.toString();
      if (responseSessionId != null && responseSessionId.isNotEmpty) {
        _chatSessionId = responseSessionId;
        await _persistChatSession(responseSessionId);
      }
      final messages = (response['messages'] as List<dynamic>?)
              ?.map((item) => item.toString())
              .toList() ??
          const <String>[];
      final rendered = messages.isEmpty ? 'No response from assistant.' : messages.join('\n\n');
      if (mounted) {
        setState(() => _chatOutput = rendered);
      }
    } on DioException catch (error) {
      final status = error.response?.statusCode;
      final body = error.response?.data;
      if (mounted) {
        setState(() {
          _chatOutput = 'Chat request failed'
              '${status != null ? ' (HTTP $status)' : ''}'
              ': ${body ?? error.message}';
        });
      }
    }
  }

  Future<void> _loadChatSession() async {
    final user = ref.read(authRepositoryProvider).user;
    if (user == null) return;
    final storage = ref.read(tokenStorageProvider);
    final savedSessionId = await storage.readChatSessionId(user.id);
    if (!mounted) return;
    setState(() => _chatSessionId = savedSessionId);
  }

  Future<void> _persistChatSession(String sessionId) async {
    final user = ref.read(authRepositoryProvider).user;
    if (user == null) return;
    final storage = ref.read(tokenStorageProvider);
    await storage.writeChatSessionId(user.id, sessionId);
  }

  Widget _sectionCard({
    required String title,
    required Widget child,
    String? subtitle,
  }) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
            if (subtitle != null) ...[
              const SizedBox(height: 4),
              Text(subtitle, style: const TextStyle(color: Colors.black54)),
            ],
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
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
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 760),
            child: RefreshIndicator(
              onRefresh: () async {
                await _loadCategories();
                await _loadExpenses();
              },
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                children: [
                  _sectionCard(
                    title: 'Add expense',
                    subtitle: 'Enter amount, notes, and optional category.',
                    child: Column(
                      children: [
                        TextField(
                          controller: _amountController,
                          decoration: const InputDecoration(labelText: 'Amount'),
                          keyboardType: TextInputType.number,
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _descriptionController,
                          decoration: const InputDecoration(labelText: 'Description'),
                        ),
                        const SizedBox(height: 12),
                        DropdownButtonFormField<int?>(
                          initialValue: _selectedCategoryId,
                          decoration: const InputDecoration(labelText: 'Category (optional)'),
                          items: [
                            const DropdownMenuItem<int?>(
                              value: null,
                              child: Text('Auto categorize'),
                            ),
                            ..._categories.map(
                              (category) => DropdownMenuItem<int?>(
                                value: category['id'] as int,
                                child: Text(category['name']?.toString() ?? ''),
                              ),
                            ),
                          ],
                          onChanged: (value) => setState(() => _selectedCategoryId = value),
                        ),
                        const SizedBox(height: 14),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: _addExpense,
                            child: const Text('Save expense'),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  _sectionCard(
                    title: 'Your expenses',
                    subtitle: 'Tap edit to update amount, description, or category.',
                    child: _expenses.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.symmetric(vertical: 10),
                            child: Text(
                              'No expenses yet. Add your first one above.',
                              style: TextStyle(color: Colors.black54),
                            ),
                          )
                        : Column(
                            children: _expenses
                                .map(
                                  (item) => Card(
                                    margin: const EdgeInsets.only(bottom: 10),
                                    child: ListTile(
                                      contentPadding: const EdgeInsets.symmetric(
                                        horizontal: 14,
                                        vertical: 6,
                                      ),
                                      title: Text(
                                        '\$${item['amount']}',
                                        style: const TextStyle(
                                          fontWeight: FontWeight.w600,
                                          fontSize: 16,
                                        ),
                                      ),
                                      subtitle: Padding(
                                        padding: const EdgeInsets.only(top: 4),
                                        child: Text(
                                          '${item['description']?.toString() ?? 'No description'}\n'
                                          'Category: ${_categoryNameForId(item['category_id'] as int?)}',
                                        ),
                                      ),
                                      isThreeLine: true,
                                      trailing: IconButton(
                                        icon: const Icon(Icons.edit),
                                        onPressed: () => _showEditExpenseDialog(item),
                                      ),
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                  ),
                  const SizedBox(height: 14),
                  _sectionCard(
                    title: 'Chat with agent',
                    subtitle: 'Ask for advice or log an expense in natural language.',
                    child: Column(
                      children: [
                        TextField(
                          controller: _chatController,
                          maxLines: 3,
                          minLines: 1,
                          decoration: const InputDecoration(labelText: 'Message'),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: _sendChat,
                            child: const Text('Send'),
                          ),
                        ),
                        if (_chatOutput.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.blue.shade50,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(_chatOutput),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
