# Contributing to GH0STB1T

Thank you for your interest in contributing to GH0STB1T.

Please review the guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check the [issue tracker](https://github.com/kariemoorman/ghostbit/issues) to avoid duplicates
2. Gather information about the bug:
   - Your OS and Python version
   - GH0STB1T version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages or logs

Create an issue with:
- Clear, descriptive title
- Detailed description
- Minimal reproducible example
- System information

### Suggesting Enhancements

Enhancement suggestions are welcome! 

Please:
1. Check existing issues/discussions first
2. Describe the feature clearly
3. Explain the use case
4. Consider backward compatibility

### Pull Requests

1. **Fork and Clone**
   ```bash
   git clone https://github.com/kariemoorman/ghostbit.git
   cd ghostbit
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Make Changes**
   - Write clear, concise code
   - Follow the existing code style
   - Add tests for new features
   - Update documentation as needed

5. **Run Tests**
   ```bash
   # Run all tests
   pytest
   
   # Run with coverage
   pytest --cov=ghostbit --cov-report=html
   
   # Run specific tests
   pytest tests/test_specific.py
   ```

6. **Format Code**
   ```bash
   # Format with Black
   black .
   
   # Lint with Ruff
   ruff check .
   
   # Type check
   mypy .
   ```

7. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation changes
   - `style:` formatting, missing semicolons, etc.
   - `refactor:` code restructuring
   - `test:` adding tests
   - `chore:` maintenance tasks

8. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use Black for formatting (line length: 100)
- Use type hints where appropriate
- Write docstrings for public APIs (Google style)
- Keep functions focused and small

### Testing

- Write tests for new features
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use descriptive test names
- Mock external dependencies

Example test:
```python
def test_encode_with_password():
    """Test encoding with password protection."""
    coder = AudioMultiFormatCoder()
    coder.encode_files_multi_format(
        carrier_file='test.wav',
        secret_files=['secret.txt'],
        output_file='output.wav',
        password='testpassword',
        quality_mode=EncodeMode.NORMAL_QUALITY
    )
    assert os.path.exists('output.wav')
```

### Documentation

- Update README.md for user-facing changes
- Update CHANGELOG.md following Keep a Changelog format
- Add docstrings to new functions/classes
- Update type hints
- Include usage examples

### Commit Messages

Good commit message:
```
feat: add support for OGG Vorbis format

- Implement OGG file reading/writing
- Add conversion methods for OGG format
- Update supported formats documentation
- Add tests for OGG encoding/decoding

Closes #123
```

## Project Structure

```
ghostbit
├── CHANGELOG.md
├── CONTRIBUTING.md
├── Dockerfile
├── LICENSE
├── Makefile
├── README.md
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── assets
│   └── ghostbit.png
├── src
│   └── ghostbit
│       ├── __init__.py
│       ├── __main__.py
│       ├── audiostego
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── cli
│       │   │   ├── __init__.py
│       │   │   └── audiostego_cli.py
│       │   ├── core
│       │   │   ├── __init__.py
│       │   │   ├── audio_multiformat_coder.py
│       │   │   └── audio_steganography.py
│       │   └── skills
│       │       ├── __init__.py
│       │       ├── capacity
│       │       │   └── SKILL.md
│       │       ├── steganography
│       │       │   └── SKILL.md
│       │       └── troubleshooting
│       │           └── SKILL.md
│       ├── cli.py
│       └── helpers
│           ├── __init__.py
│           ├── check_audio_requirements.py
│           └── format_argparse.py
└── tests
      └── testcases

```

## Review Process

1. All PRs require review before merging
2. CI checks must pass (tests, linting, type checking)
3. Code coverage should not decrease
4. Documentation must be updated
5. CHANGELOG.md must be updated

## Getting Help

- 💬 [GitHub Discussions](https://github.com/kariemoorman/ghostbit/discussions)
- 🐛 [Issue Tracker](https://github.com/kariemoorman/ghostbit/issues)

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for contributing to GH0STB1T!
