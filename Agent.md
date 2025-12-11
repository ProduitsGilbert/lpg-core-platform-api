# Coding Agent Guidelines

## Overview

This document outlines the coding standards, workflow guidelines, and best practices that all coding agents must follow when working on the LPG Core Platform API project. These guidelines ensure consistency, maintainability, and adherence to the established CI/CD workflow.

## 1. Git Workflow

### Branching Strategy
- **main**: Always deployable production code
- **dev**: Active development branch for integration
- **feature/* branches**: All new development work

### Development Process
1. Create feature branches from `dev`: `git checkout -b feature/your-feature-name`
2. Make changes following the guidelines below
3. Test locally using the appropriate environment
4. Commit with clear, descriptive messages
5. Create Pull Request to `dev` for review
6. After approval and merge to `dev`, create PR to `main` when ready for deployment

### Commit Guidelines
- Use clear, descriptive commit messages
- Reference issue numbers when applicable: `feat: add user authentication (#123)`
- Keep commits focused on single changes
- Use conventional commit format:
  - `feat:` - New features
  - `fix:` - Bug fixes
  - `docs:` - Documentation
  - `style:` - Code style changes
  - `refactor:` - Code refactoring
  - `test:` - Test additions/modifications
  - `chore:` - Maintenance tasks

## 2. Environment Management

### Environment Variables
- All configuration must use environment variables defined in `settings.py`
- Never hardcode sensitive information (API keys, database credentials, etc.)
- Use the established `.env` file pattern:
  - `.env.example` - Template with all variables (committed to git)
  - `.env.dev` - Development configuration (not committed)
  - `.env.prod` - Production configuration (not committed)

### APP_ENV Variable
- Must set `APP_ENV=dev` for development, `APP_ENV=prod` for production
- This controls which `.env` file is loaded automatically
- Update `settings.py` to add new environment variables following the existing pattern

## 3. Code Quality Standards

### Python Code Style
- Follow PEP 8 standards
- Use type hints for all function parameters and return values
- Maximum line length: 88 characters (Black default)
- Use descriptive variable and function names
- Add docstrings to all public functions and classes

### Error Handling
- Use proper exception handling
- Log errors appropriately using the established logging framework
- Return meaningful error responses to API clients
- Never expose sensitive information in error messages

### Testing
- Write unit tests for all new functionality
- Maintain test coverage above 80%
- Use pytest framework as established
- Test both success and failure scenarios
- Mock external dependencies in tests

## 4. API Development

### REST API Guidelines
- Follow RESTful conventions
- Use proper HTTP status codes
- Implement consistent error response format
- Document all endpoints with OpenAPI/Swagger
- Version APIs appropriately (`/api/v1/`)

### Database Operations
- Use SQLAlchemy ORM as established
- Implement proper transaction management
- Use connection pooling
- Never execute raw SQL unless absolutely necessary
- Implement proper indexing for performance

### Security
- Validate all input data
- Implement authentication and authorization
- Use HTTPS in production
- Implement rate limiting where appropriate
- Log security events

## 5. Docker and Deployment

### Containerization
- Ensure all code runs in Docker containers
- Use multi-stage builds for optimization
- Follow the established Dockerfile pattern
- Test containers locally before deployment

### CI/CD Compliance
- All code must pass CI checks before merging
- Ensure Docker builds succeed
- Maintain backward compatibility
- Update documentation for any breaking changes

## 6. Documentation

### Code Documentation
- Update docstrings for any modified functions
- Document complex business logic
- Explain non-obvious code decisions

### API Documentation
- Keep OpenAPI specifications up to date
- Document all request/response formats
- Include examples for all endpoints

### README Updates
- Update README.md for any new features or setup changes
- Document environment setup procedures
- Include troubleshooting guides

## 7. Code Review Checklist

Before submitting a Pull Request, ensure:

- [ ] Code follows established patterns and conventions
- [ ] All tests pass locally
- [ ] New functionality is covered by tests
- [ ] Documentation is updated
- [ ] Environment variables are properly configured
- [ ] Docker builds and runs successfully
- [ ] No sensitive data is committed
- [ ] Commit messages are clear and descriptive
- [ ] Backward compatibility is maintained

## 8. Communication

### Pull Request Descriptions
- Clearly describe what the changes accomplish
- Reference related issues or requirements
- Explain any architectural decisions
- Include testing instructions if needed

### Code Comments
- Use comments to explain complex logic
- Avoid obvious comments that just restate the code
- Document assumptions and limitations

## 9. Performance Considerations

- Optimize database queries
- Implement caching where appropriate
- Monitor memory usage
- Use async operations for I/O bound tasks
- Profile code for bottlenecks

## 10. Monitoring and Logging

- Implement proper logging levels (DEBUG, INFO, WARNING, ERROR)
- Include relevant context in log messages
- Monitor application health endpoints
- Log performance metrics
- Use structured logging format

---

## Agent Responsibility

As a coding agent working on this project, you must:

1. **Read and understand this document** before making any changes
2. **Follow all established patterns** in the codebase
3. **Maintain consistency** with existing code style and architecture
4. **Test thoroughly** before submitting changes
5. **Document everything** - code, APIs, and processes
6. **Never break production** - ensure all changes are backward compatible
7. **Communicate clearly** in commit messages and PR descriptions

Failure to follow these guidelines may result in rejected Pull Requests and requests for rework.

