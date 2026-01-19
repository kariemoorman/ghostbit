## Description
<!-- Provide a clear description of what this PR does -->

## Type of Change
<!-- Mark the relevant option with an "x" -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Code refactoring
- [ ] Performance improvement
- [ ] Test addition/modification

## Related Issue
<!-- Link to the issue this PR addresses -->
Closes #

## Changes Made
<!-- List the main changes in bullet points -->
- 
- 
- 

## Testing
<!-- Describe the tests you ran to verify your changes -->

### Test Configuration
- **OS**: 
- **Python Version**: 
- **Pydub Version**: 
- **FFmpeg Version**: 
- **Soundfile Version**: 
- **Pycrytodome Version**: 

### Test Cases
- [ ] Unit tests pass locally
- [ ] Integration tests pass locally
- [ ] Manual testing completed
- [ ] Edge cases tested

### Test Commands
```bash
# Commands used for testing
ghostbit audio test --create-carrier
pytest tests/
```

### Code Quality Commands 
```bash
mypy src/ghostbit
ruff check .
black .
```

## Screenshots/Output
<!-- If applicable, add screenshots or command output -->

```
[Paste output here]
```

## Checklist
<!-- Mark completed items with an "x" -->


### Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] I have run `make test`

### Code Quality
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [ ] I have run `make format` (Black)
- [ ] I have run `make lint` (Ruff)
- [ ] I have run `make type` (MyPy)
- [ ] I have run `make clean` (Clean up test artifacts)

### Documentation
- [ ] I have updated the documentation accordingly
- [ ] I have updated the CHANGELOG.md

### Commits
- [ ] My commits follow the Conventional Commits specification
- [ ] My commit messages are clear and descriptive

## Breaking Changes
<!-- If this PR includes breaking changes, describe them and provide migration instructions -->

## Additional Notes
<!-- Any additional information for reviewers -->

## Reviewer Notes
<!-- For the reviewer: What should they pay special attention to? -->
