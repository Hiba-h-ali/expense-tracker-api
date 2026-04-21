import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_api_client.dart';
import 'models.dart';
import 'token_storage.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

final authDioProvider = Provider<Dio>((ref) {
  return Dio(
    BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ),
  );
});

final tokenStorageProvider = Provider<TokenStorage>((ref) {
  return TokenStorage(const FlutterSecureStorage());
});

final authApiClientProvider = Provider<AuthApiClient>((ref) {
  return AuthApiClient(ref.read(authDioProvider));
});

class AuthState {
  const AuthState({
    this.user,
    this.tokens,
    this.isLoading = false,
    this.errorMessage,
  });

  final AuthUser? user;
  final AuthTokens? tokens;
  final bool isLoading;
  final String? errorMessage;

  bool get isAuthenticated => user != null && tokens != null;

  AuthState copyWith({
    AuthUser? user,
    AuthTokens? tokens,
    bool? isLoading,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AuthState(
      user: user ?? this.user,
      tokens: tokens ?? this.tokens,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

class AuthRepository extends StateNotifier<AuthState> {
  AuthRepository(this._api, this._storage) : super(const AuthState());

  final AuthApiClient _api;
  final TokenStorage _storage;
  bool _refreshInFlight = false;

  Future<void> bootstrap() async {
    final tokens = await _storage.readTokens();
    if (tokens == null) {
      state = const AuthState();
      return;
    }
    try {
      final user = await _api.me(tokens.accessToken);
      state = AuthState(user: user, tokens: tokens);
    } catch (_) {
      final refreshed = await _tryRefresh(tokens.refreshToken);
      if (!refreshed) {
        await _storage.clear();
        state = const AuthState();
      }
    }
  }

  Future<void> signUp(RegisterPayload payload) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _api.register(payload);
      await signIn(LoginPayload(email: payload.email, password: payload.password));
    } catch (error) {
      state = state.copyWith(isLoading: false, errorMessage: '$error');
    }
  }

  Future<void> signIn(LoginPayload payload) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final tokens = await _api.login(payload);
      await _storage.writeTokens(tokens);
      final user = await _api.me(tokens.accessToken);
      state = AuthState(user: user, tokens: tokens, isLoading: false);
    } catch (error) {
      state = state.copyWith(isLoading: false, errorMessage: '$error');
    }
  }

  Future<void> signOut() async {
    final tokens = state.tokens;
    if (tokens != null) {
      try {
        await _api.logout(tokens.refreshToken);
      } catch (_) {
        // Network failure during logout should not block local session cleanup.
      }
    }
    await _storage.clear();
    state = const AuthState();
  }

  Future<bool> refreshSession() async {
    final refreshToken = state.tokens?.refreshToken;
    if (refreshToken == null) {
      return false;
    }
    return _tryRefresh(refreshToken);
  }

  Future<bool> _tryRefresh(String refreshToken) async {
    if (_refreshInFlight) {
      return false;
    }
    _refreshInFlight = true;
    try {
      final newTokens = await _api.refresh(refreshToken);
      await _storage.writeTokens(newTokens);
      final user = await _api.me(newTokens.accessToken);
      state = AuthState(user: user, tokens: newTokens, isLoading: false);
      return true;
    } catch (_) {
      await _storage.clear();
      state = const AuthState();
      return false;
    } finally {
      _refreshInFlight = false;
    }
  }
}

final authRepositoryProvider =
    StateNotifierProvider<AuthRepository, AuthState>((ref) {
  return AuthRepository(
    ref.read(authApiClientProvider),
    ref.read(tokenStorageProvider),
  );
});
