import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/media.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _register = false;
  bool _busy = false;
  bool _hide = true;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final state = context.read<AppState>();
    try {
      if (_register) {
        await state.register(_name.text, _email.text, _password.text);
      } else {
        await state.login(_email.text, _password.text);
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Palette.slate,
      body: Stack(
        fit: StackFit.expand,
        children: [
          const LoopingVideo(video: Media.loginVideo, poster: Media.loginPoster),
          DecoratedBox(decoration: BoxDecoration(gradient: Palette.photoShade(top: 0.35, bottom: 0.9, start: 0))),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Appear(
                        child: Text('QissaGo', style: display(60, color: Colors.white), textAlign: TextAlign.center),
                      ),
                      const SizedBox(height: 36),
                      Appear(
                        index: 2,
                        child: Container(
                          padding: const EdgeInsets.all(22),
                          decoration: BoxDecoration(
                            color: Palette.paper.withValues(alpha: 0.96),
                            borderRadius: BorderRadius.circular(28),
                            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.25), blurRadius: 30)],
                          ),
                          child: Form(
                            key: _form,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Text(_register ? 'Create account' : 'Welcome back', style: display(28)),
                                const SizedBox(height: 20),
                                if (_register) ...[
                                  TextFormField(
                                    controller: _name,
                                    textCapitalization: TextCapitalization.words,
                                    decoration: fieldStyle('Name', icon: Icons.person_outline),
                                    validator: (v) => (v ?? '').trim().length < 2 ? 'Enter your name' : null,
                                  ),
                                  const SizedBox(height: 12),
                                ],
                                TextFormField(
                                  controller: _email,
                                  keyboardType: TextInputType.emailAddress,
                                  decoration: fieldStyle('Email', icon: Icons.mail_outline),
                                  validator: (v) => (v ?? '').contains('@') ? null : 'Enter a valid email',
                                ),
                                const SizedBox(height: 12),
                                TextFormField(
                                  controller: _password,
                                  obscureText: _hide,
                                  decoration: fieldStyle('Password', icon: Icons.lock_outline).copyWith(
                                    suffixIcon: IconButton(
                                      icon: Icon(_hide ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                                      onPressed: () => setState(() => _hide = !_hide),
                                    ),
                                  ),
                                  validator: (v) => (v ?? '').length < 6 ? 'At least 6 characters' : null,
                                  onFieldSubmitted: (_) => _submit(),
                                ),
                                const SizedBox(height: 20),
                                FilledButton(
                                  onPressed: _busy ? null : _submit,
                                  child: _busy
                                      ? const SizedBox(
                                          width: 22,
                                          height: 22,
                                          child: CircularProgressIndicator(strokeWidth: 2.4, color: Palette.onPrimary),
                                        )
                                      : Text(_register ? 'Sign up' : 'Log in'),
                                ),
                                const SizedBox(height: 8),
                                TextButton(
                                  onPressed: _busy ? null : () => setState(() => _register = !_register),
                                  child: Text(_register ? 'I already have an account' : 'Create an account'),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
