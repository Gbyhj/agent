# Code Review Skill

## When to use
User asks to review, audit, check, or analyze code quality.

## Process
1. Read the target file(s) with read_file tool
2. Check for: injection · auth bypass · path traversal · hardcoded secrets
3. Check for: N+1 queries · memory leaks · race conditions
4. Check for: naming · complexity · dead code
5. Report each finding: location + severity + description + fix

## Output format
```markdown
## 🔐 Security Review
### [severity] Location: description
→ Fix: specific code change

## ⚡ Performance
### [severity] Location: description  
→ Fix: specific code change

## 📏 Code Quality
### [severity] Location: description
→ Fix: specific code change
```

## Severity levels
- 🔴 Critical: RCE · data loss · auth bypass
- 🟡 Warning: performance · edge case · tech debt
- 🟢 Suggestion: naming · style · minor refactor
