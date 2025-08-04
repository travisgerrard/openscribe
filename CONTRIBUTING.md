# Contributing to Professional Transcriber

Thank you for your interest in contributing to Professional Transcriber! This document provides guidelines and information for contributors.

## Code of Conduct

This project is committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and considerate in all interactions.

## How to Contribute

### Reporting Issues

Before creating an issue, please:

1. Check if the issue has already been reported
2. Search the existing issues and discussions
3. Provide detailed information including:
   - Operating system and version
   - Python and Node.js versions
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Relevant error messages or logs

### Feature Requests

When requesting features:

1. Clearly describe the feature and its use case
2. Explain why this feature would be valuable
3. Consider implementation complexity
4. Check if similar functionality already exists

### Pull Requests

#### Before Submitting

1. **Fork the repository** and create a feature branch
2. **Follow the coding standards** (see below)
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass** locally
6. **Test on multiple platforms** if applicable

#### Pull Request Guidelines

- Use descriptive commit messages
- Keep changes focused and atomic
- Include tests for new functionality
- Update relevant documentation
- Add a description of changes in the PR
- Reference related issues

## Development Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- Git

### Local Development

1. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/professional-transcriber.git
   cd professional-transcriber
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   npm install
   ```

3. **Set up pre-commit hooks** (optional)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. **Run tests**
   ```bash
   pytest
   npm test
   ```

## Coding Standards

### Python

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for public functions and classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable and function names

### JavaScript/Electron

- Follow ESLint configuration
- Use consistent indentation (2 spaces)
- Prefer const/let over var
- Use meaningful variable names
- Add JSDoc comments for complex functions

### General

- Write clear, descriptive commit messages
- Keep changes focused and atomic
- Add comments for complex logic
- Follow existing code patterns and conventions

## Testing

### Running Tests

```bash
# Python tests
pytest                    # All tests
pytest tests/unit/        # Unit tests only
pytest tests/integration/ # Integration tests only
pytest tests/performance/ # Performance tests only

# JavaScript tests
npm test                  # Linting and basic tests
npm run lint             # ESLint only
```

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies
- Keep tests focused and independent

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Include type hints where helpful
- Document complex algorithms or business logic
- Keep comments up to date with code changes

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Keep installation and setup instructions current
- Document configuration options

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes (backward compatible)

### Release Checklist

Before each release:

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Changelog is updated
- [ ] Version numbers are updated
- [ ] Release notes are prepared

## Getting Help

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions and general discussion
- **Documentation**: Check the docs/ directory for detailed documentation

## Recognition

Contributors will be recognized in:

- The project README
- Release notes
- GitHub contributors page

Thank you for contributing to Professional Transcriber! 