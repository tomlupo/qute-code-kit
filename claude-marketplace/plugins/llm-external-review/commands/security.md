# /llm-external-review:security

> **This command invokes EXTERNAL AI (Codex) for security review. Claude must NOT do this review itself.**

Security-focused code review using EXTERNAL AI to identify vulnerabilities.

## Usage

```
/llm-external-review:security <file|directory> [--depth <level>]
```

## Arguments

- `<file|directory>` - File or directory to scan
- `--depth` - (Optional) Analysis depth: quick, standard, deep (default: standard)

## Behavior

1. **Scan code for security patterns**
   - Input validation
   - Authentication/authorization
   - Data handling
   - Cryptography usage
   - Dependencies

2. **Check against OWASP Top 10**
   - A01: Broken Access Control
   - A02: Cryptographic Failures
   - A03: Injection
   - A04: Insecure Design
   - A05: Security Misconfiguration
   - A06: Vulnerable Components
   - A07: Auth Failures
   - A08: Data Integrity Failures
   - A09: Logging Failures
   - A10: SSRF

3. **Generate security report**:
   ```
   🔒 Security Review
   ━━━━━━━━━━━━━━━━━

   File: src/api/auth.py

   ## Vulnerability Summary
   | Severity | Count |
   |----------|-------|
   | 🔴 Critical | 2 |
   | 🟠 High | 3 |
   | 🟡 Medium | 5 |
   | 🔵 Low | 2 |

   ## Critical Vulnerabilities

   ### 1. SQL Injection (A03)
   **Location**: Line 45
   **Code**:
   ```python
   query = f"SELECT * FROM users WHERE id = {user_id}"
   ```
   **Risk**: Attacker can execute arbitrary SQL
   **Fix**:
   ```python
   query = "SELECT * FROM users WHERE id = ?"
   cursor.execute(query, (user_id,))
   ```

   ### 2. Hardcoded Secret (A02)
   **Location**: Line 12
   **Code**:
   ```python
   SECRET_KEY = "abc123supersecret"
   ```
   **Risk**: Secret exposed in source code
   **Fix**: Use environment variable

   ## OWASP Coverage
   | Category | Status | Issues |
   |----------|--------|--------|
   | A01: Access Control | ⚠️ | 1 |
   | A02: Crypto | 🔴 | 2 |
   | A03: Injection | 🔴 | 1 |
   | A04: Design | ✅ | 0 |
   | ... | | |

   ## Recommendations
   1. **Immediate**: Fix SQL injection and remove hardcoded secrets
   2. **Short-term**: Add input validation layer
   3. **Long-term**: Implement security middleware
   ```

## Example

```
/llm-external-review:security src/api/ --depth deep

# Output:
🔒 Security Review (deep scan)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scanned: 12 files

## Critical Issues (fix immediately)
1. SQL Injection in handler.py:45
2. XSS vulnerability in render.py:78
3. Hardcoded AWS keys in config.py:12

## High Priority
4. Missing CSRF protection
5. Insecure cookie settings
6. No rate limiting on auth endpoints

## Dependency Vulnerabilities
- requests 2.25.0: CVE-2023-XXXX (upgrade to 2.31.0)
- pyyaml 5.3: CVE-2022-XXXX (upgrade to 6.0)

Total scan time: 45s
```

## Depth Levels

- **quick**: Syntax patterns only, <10s
- **standard**: Pattern + dataflow analysis, <1min
- **deep**: Full taint analysis + dependency check, <5min
