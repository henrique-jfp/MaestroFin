# Changelog - Maestro Financeiro

## [2.0.0] - 2025-11-18

### 🚀 Major Features
- **Non-blocking Async Execution**: Refactored `/sincronizar` to use `asyncio.run_in_executor()` for non-blocking bank synchronization
  - Multiple users can now sync simultaneously without blocking other commands
  - Event loop remains responsive during heavy operations
  - Solves critical concurrency issue affecting user experience

### ✨ Improvements
- **Account Pagination**: Implemented full pagination support for fetching bank accounts and investments from Pluggy API
  - Ensures no accounts are hidden on subsequent pages (fixes missing "Cofrinho" accounts)
- **Investment Detection**: Automatic detection of investments in checking accounts via `automaticallyInvestedBalance`
- **Architecture**: Moved synchronous blocking operations to separate threads following python-telegram-bot best practices

### 🐛 Bug Fixes
- Fixed `ZeroDivisionError` in report template when financial data is zero
- Fixed `UnboundLocalError` in PDF generation error handling
- Removed duplicate exception handling that was masking original errors
- Improved error messaging and user feedback

### 🧹 Chores
- Removed obsolete test files (`test_gemini_model.py`, `test_pluggy_oauth.py`)
- Removed deprecated migration scripts (`apply_migration_*.py`)
- Removed obsolete documentation files (bugfix and configuration guides consolidated into main docs)
- Cleaned up `__pycache__` directories
- Code cleanup and refactoring

---

## [1.0.0] - Previous Release

### Features
- Open Finance OAuth integration with 100+ bank support
- Telegram bot with comprehensive financial management
- Transaction categorization and analytics
- Investment tracking
- Financial reports and gamification
- OCR for receipt processing

---

## Release Notes

### v2.0.0 - Breaking Changes / Important Updates
- **Concurrency**: Bot now handles multiple simultaneous user requests without blocking
- **Scalability**: Can handle N concurrent users making requests
- **Reliability**: Improved error handling and recovery

### Migration Guide
No migration required. This is a drop-in improvement that maintains backward compatibility.

---

