import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'models.dart';

class TokenStorage {
  TokenStorage(this._storage);

  static const _kAccessToken = 'access_token';
  static const _kRefreshToken = 'refresh_token';
  static const _kTokenType = 'token_type';

  final FlutterSecureStorage _storage;

  Future<AuthTokens?> readTokens() async {
    final accessToken = await _storage.read(key: _kAccessToken);
    final refreshToken = await _storage.read(key: _kRefreshToken);
    final tokenType = await _storage.read(key: _kTokenType) ?? 'bearer';
    if (accessToken == null || refreshToken == null) {
      return null;
    }
    return AuthTokens(
      accessToken: accessToken,
      refreshToken: refreshToken,
      tokenType: tokenType,
    );
  }

  Future<void> writeTokens(AuthTokens tokens) async {
    await _storage.write(key: _kAccessToken, value: tokens.accessToken);
    await _storage.write(key: _kRefreshToken, value: tokens.refreshToken);
    await _storage.write(key: _kTokenType, value: tokens.tokenType);
  }

  Future<void> clear() async {
    await _storage.delete(key: _kAccessToken);
    await _storage.delete(key: _kRefreshToken);
    await _storage.delete(key: _kTokenType);
  }
}
