# MCP Validator Repository - TODO List

## Priority 1: Code Organization and Cleanup

1. **Consolidate Test Scripts**
   - [x] Move redundant HTTP testing scripts to archive
   - [ ] Create a unified testing API for both HTTP and STDIO servers
   - [ ] Standardize test reporting formats

2. **Documentation Updates**
   - [ ] Update main README.md with current implementation details
   - [ ] Create a unified documentation structure
   - [ ] Add developer documentation for extending the test framework

3. **Code Standardization**
   - [ ] Apply consistent naming conventions across codebase
   - [ ] Create style guide for contributors
   - [ ] Fix any remaining linting issues

## Priority 2: Technical Improvements

1. **Error Handling Enhancements**
   - [ ] Implement consistent error handling patterns
   - [ ] Add clear, actionable error messages
   - [ ] Add detailed logging for debugging

2. **Testing Framework Improvements**
   - [ ] Add more granular test categories
   - [ ] Implement parameterized tests for different protocol versions
   - [ ] Improve test coverage reporting

3. **Server Implementation Improvements**
   - [ ] Add missing optional protocol features
   - [ ] Optimize performance for large requests/responses
   - [ ] Add configuration options for server behavior

## Priority 3: Feature Additions

1. **New Protocol Support**
   - [ ] Prepare for next protocol version updates
   - [ ] Add streaming capability tests
   - [ ] Implement utilities capability

2. **Additional Test Types**
   - [ ] Add stress/load testing
   - [ ] Add security validation tests
   - [ ] Add cross-version compatibility tests

## Notes and Decisions

- Keep archive directory until we confirm no functionality is lost
- Next protocol version expected in Q3 2025 - prepare validation framework
- Consider refactoring to support more transport types in the future 