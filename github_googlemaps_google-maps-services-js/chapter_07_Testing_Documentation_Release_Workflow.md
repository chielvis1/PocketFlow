# Chapter 7: Testing, Documentation & Release Workflow  

# Chapter 7: Testing, Documentation & Release Workflow

## Introduction

In this chapter we’ll cover the vital “plumbing” that surrounds our TypeScript-first Google Maps client library: writing tests with Jest, generating API docs with TypeDoc, and automating releases via GitHub Actions (release-please). We’ll also touch on project governance—licenses and contribution guidelines—so you can confidently develop, document, and ship new features.

---

## 7.1 Testing with Jest

### 7.1.1 Installing & Configuring Jest

First, add Jest and friends:

```bash
npm install --save-dev jest ts-jest @types/jest
```

Create a `jest.config.js` at the repo root:

```js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/**/*.test.ts'],
  moduleFileExtensions: ['ts', 'js', 'json'],
  collectCoverage: true,
  coverageDirectory: '<rootDir>/coverage',
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 85,
      statements: 85,
    },
  },
};
```

### 7.1.2 Unit vs. Integration Tests

- **Unit tests**: isolate a single class or function, mocking external HTTP calls.
- **Integration tests**: exercise actual HTTP requests against a test key or stub server.

Example unit test for `GeocodingService`:

```ts
// src/services/geocoding.test.ts
import { GeocodingService } from './geocoding';
import nock from 'nock';

describe('GeocodingService (unit)', () => {
  const service = new GeocodingService({ apiKey: 'TEST_KEY' });

  beforeAll(() => {
    nock('https://maps.googleapis.com')
      .get('/maps/api/geocode/json')
      .query(true)
      .reply(200, { results: [{ formatted_address: '123 Test St' }], status: 'OK' });
  });

  it('should return formatted address', async () => {
    const resp = await service.geocode({ address: 'Test St' });
    expect(resp.results[0].formatted_address).toBe('123 Test St');
  });
});
```

For integration tests, skip `nock`, point at a sandbox environment, and guard with an `API_KEY` env var.

```ts
// src/integration/geocoding.integration.test.ts
import { GeocodingService } from '../services/geocoding';

describe('GeocodingService (integration)', () => {
  const key = process.env.GEOCODING_KEY;
  if (!key) {
    console.warn('Skipping integration tests; GEOCODING_KEY not set.');
    return;
  }
  const service = new GeocodingService({ apiKey: key });

  it('resolves a real address', async () => {
    const res = await service.geocode({ address: 'New York, NY' });
    expect(res.results.length).toBeGreaterThan(0);
  });
});
```

Run tests with:

```bash
npm test
```

---

## 7.2 Generating Documentation with TypeDoc

### 7.2.1 Installing & Configuring TypeDoc

```bash
npm install --save-dev typedoc typedoc-plugin-markdown
```

Add a `typedoc.json`:

```json
{
  "entryPoints": ["src/index.ts"],
  "out": "docs/api",
  "plugin": ["typedoc-plugin-markdown"],
  "excludePrivate": true,
  "excludeInternal": true,
  "includeVersion": true
}
```

### 7.2.2 Generating Docs

Add to `package.json`:

```json
{
  "scripts": {
    "docs": "typedoc"
  }
}
```

Then:

```bash
npm run docs
```

This produces markdown files under `docs/api/`. Hook these into your static site generator (GitHub Pages, Docusaurus, etc.).

---

## 7.3 Automating Releases with GitHub Actions

We follow **Conventional Commits**, generate a changelog, and publish to npm automatically.

### 7.3.1 Conventional Commits & Changelog

Commit messages look like:

```
feat(geocoding): add region bias option
fix(client): handle network timeouts
```

We use `release-please` to parse these and bump versions.

### 7.3.2 GitHub Workflow (`.github/workflows/release.yml`)

```yaml
name: Release

on:
  push:
    branches:
      - main

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/release-please-action@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          release-type: node
          package-name: "@your-org/maps-client"
          changelog-types: feat, fix, perf, docs
```

This action will:
1. Analyze commits since last tag.
2. Generate or update `CHANGELOG.md`.
3. Bump `package.json` version.
4. Create a new GitHub Release.

### 7.3.3 Automatic npm Publishing

Add a second job that runs on the release tag:

```yaml
  publish:
    needs: release
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

Store your `NPM_TOKEN` in GitHub Secrets. After the release PR is merged, the `publish` job will push the package to npm.

---

## 7.4 Governance

### 7.4.1 License: Apache 2.0

Our project is Apache-2.0 licensed. The `LICENSE` file at root spells out permissions and limitations.

### 7.4.2 CONTRIBUTING.md

Defines:
- Code style (Prettier, ESLint).
- Branching strategy (`main` for release-ready code, `feat/*` and `fix/*` branches).
- Pull request checklist (tests, docs, changelog entry).

### 7.4.3 CODE_OF_CONDUCT.md

We adopt a standard Contributor Covenant. It ensures a respectful, inclusive community. Link to it in PR templates and README.

---

## Conclusion

By integrating Jest for thorough unit and integration tests, TypeDoc for clear API documentation, and GitHub Actions with release-please for automated versioning and npm publishing, we establish a robust, repeatable workflow. Coupled with clear governance docs (LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md), your thin wrapper around Google Maps services becomes a well-maintained, community-friendly open-source project. Happy coding and releasing!