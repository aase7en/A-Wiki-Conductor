# Contributing to A-Sunday Conductor

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs
1. Open a [GitHub Issue](https://github.com/aase7en/A-Wiki-Conductor/issues)
2. Use the **Bug Report** template
3. Include: OS version, app version (from title bar), steps to reproduce, expected vs actual behavior

### Suggesting Features
1. Open a [GitHub Issue](https://github.com/aase7en/A-Wiki-Conductor/issues)
2. Use the **Feature Request** template
3. Describe the problem you're trying to solve, not just the solution

### Code Contributions

```bash
# 1. Fork and clone
git clone https://github.com/YOUR-USERNAME/A-Wiki-Conductor.git
cd A-Wiki-Conductor

# 2. Install with test dependencies
python -m pip install -e .[test]

# 3. Run tests (must be green before PR)
python -m pytest tests/ -q

# 4. Create a feature branch
git checkout -b feat/your-feature-name

# 5. Make changes + write tests

# 6. Run tests again
python -m pytest tests/ -q

# 7. Push and create Pull Request
git push origin feat/your-feature-name
```

### Development Guidelines

- **Python stdlib only** — no external dependencies
- **TDD preferred** — write failing test first, then implement
- **Tests must pass** — CI runs on Windows, Ubuntu, and macOS
- **Keep PRs small** — one feature per PR
- **Update docs** — if your change affects the user guide

### Project Structure

```
src/a_conductor/     # Main application code
tests/               # Test suite (~1000 tests)
docs/                # Documentation + user guides
scripts/             # Build/install/signing scripts
.github/             # CI workflows + community files
```

## Questions?

Feel free to open an issue or start a discussion!

---

*ขอบคุณที่ร่วมพัฒนา — Thanks for contributing!*
