# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Phase 2 "Quality & Maintainability" initiatives: centralized configuration, strict typing, CI pipeline, optimized Docker image, and improved documentation.

### Changed
- Updated runtime services to use the strongly typed configuration object and custom exception hierarchy.

### Fixed
- Ensured watchers and MCP server share validated paths, preventing unsafe filesystem access.

## [0.9.0] - 2025-12-03
### Added
- MIT license, initial documentation set, and reorganized pytest suites covering core MCP flows.

### Changed
- Security fixes applied to the initial MCP server implementation before open-sourcing.

### Fixed
- Test suite stabilization ahead of releasing the first public beta.
