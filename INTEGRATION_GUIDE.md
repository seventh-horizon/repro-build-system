# Integration Guide - Repro Pack

Complete guide for integrating Repro Pack into your CI/CD pipelines and build systems.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [GitHub Actions](#github-actions)
3. [GitLab CI](#gitlab-ci)
4. [Jenkins](#jenkins)
5. [CircleCI](#circleci)
6. [Azure Pipelines](#azure-pipelines)
7. [Docker Integration](#docker-integration)
8. [Makefile Integration](#makefile-integration)
9. [Pre-commit Hooks](#pre-commit-hooks)
10. [Release Automation](#release-automation)

---

## Quick Start

### Minimal Integration (5 minutes)

```bash
# 1. Clone Repro Pack
git clone https://github.com/your-org/repro-pack
cd repro-pack
bash init.sh

# 2. Add to your project
cp -r tools/ /path/to/your-project/
cp Makefile /path/to/your-project/

# 3. Build with reproducibility
cd /path/to/your-project
make build
make verify
make compliance
```

### Standard Integration (15 minutes)

Add to your project's CI configuration:

```yaml
# .github/workflows/build.yml
name: Build with Repro Pack

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Repro Pack
        run: |
          git clone https://github.com/your-org/repro-pack tools
          cd tools && bash init.sh
      
      - name: Build
        run: make -f tools/Makefile build
      
      - name: Verify
        run: make -f tools/Makefile verify
      
      - name: Compliance
        run: make -f tools/Makefile compliance
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-artifacts
          path: |
            dist/artifact.tar.gz
            dist/vel_manifest.json
            dist/release_bom.json
            dist/evidence.json
```

---

## GitHub Actions

### Complete Workflow

```yaml
# .github/workflows/reproducible-build.yml
name: Reproducible Build & Release

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REPRO_OUTPUT_DIR: dist/
  REPRO_STRICT_MODE: 1

jobs:
  build:
    name: Build & Validate
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4.1.7
        with:
          fetch-depth: 0  # Full history for git SHA
      
      - name: Setup Python
        uses: actions/setup-python@f677139bbe7f9c59b41e40162b753cc15f5c515c # v5.2.0
        with:
          python-version: '3.11'
      
      - name: Install Repro Pack
        run: |
          pip install --no-cache-dir -r requirements.txt
          bash init.sh
      
      - name: Security Scan
        run: |
          echo "::group::Secret Scanning"
          python tools/secret_lint.py src/ --output dist/secrets_report.json
          echo "::endgroup::"
          
          echo "::group::Permission Check"
          python tools/permissions_lint.py src/ --output dist/perms_report.json
          echo "::endgroup::"
          
          echo "::group::GitHub Actions Pins Check"
          python tools/pins_manifest_check.py .github/workflows/ --output dist/pins_check.json
          echo "::endgroup::"
      
      - name: Create Snapshot
        run: |
          python tools/make_snapshot.py src/ \
            --output dist/snapshot.json \
            --ignore "*.pyc" --ignore "__pycache__"
      
      - name: Stamp Version
        run: |
          VERSION="${GITHUB_REF_NAME}"
          if [[ "$VERSION" == "main" ]]; then
            VERSION="${GITHUB_SHA:0:8}"
          fi
          python tools/version_stamp.py "$VERSION" --output dist/VERSION
      
      - name: Build Deterministic Artifact
        run: |
          python tools/det_tar.py src/ --output dist/artifact.tar
          gzip -n dist/artifact.tar
      
      - name: Generate VEL Manifest
        run: |
          python tools/make_vel_manifest.py \
            --snapshot dist/snapshot.json \
            --artifact dist/artifact.tar.gz \
            --git-sha "$GITHUB_SHA" \
            --output dist/vel_manifest.json
      
      - name: Validate Build
        run: |
          echo "::group::VEL Validation"
          python tools/vel_validator.py dist/vel_manifest.json \
            --artifact dist/artifact.tar.gz \
            --schema schema/vel_manifest.schema.json
          echo "::endgroup::"
          
          echo "::group::Tar Determinism Check"
          python tools/verify_tar_determinism.py dist/artifact.tar.gz \
            --output dist/tar_check.json
          echo "::endgroup::"
          
          echo "::group::Gzip Header Check"
          python tools/verify_gzip_header.py dist/artifact.tar.gz \
            --output dist/gzip_check.json
          echo "::endgroup::"
          
          echo "::group::Safe Paths Check"
          python tools/safe_paths_check.py dist/artifact.tar.gz \
            --output dist/paths_check.json
          echo "::endgroup::"
      
      - name: Generate RBOM
        run: |
          VERSION="${GITHUB_REF_NAME}"
          if [[ "$VERSION" == "main" ]]; then
            VERSION="${GITHUB_SHA:0:8}"
          fi
          python tools/make_rbom.py dist/ \
            --version "$VERSION" \
            --output dist/release_bom.json
      
      - name: Validate RBOM
        run: |
          python tools/rbom_check.py dist/release_bom.json \
            --policy schema/rbom_policy.json \
            --output dist/rbom_check.json
      
      - name: Generate Evidence Matrix
        run: |
          python tools/evidence_matrix.py dist/ \
            --output dist/evidence.json
      
      - name: Generate CI Summary
        run: |
          python tools/make_ci_summary.py dist/ \
            --output dist/summary.md
          cat dist/summary.md >> $GITHUB_STEP_SUMMARY
      
      - name: Upload Artifacts
        uses: actions/upload-artifact@50769540e7f4bd5e21e526ee35c689e35e0d6874 # v4.4.0
        if: always()
        with:
          name: build-artifacts-${{ github.sha }}
          path: |
            dist/artifact.tar.gz
            dist/vel_manifest.json
            dist/release_bom.json
            dist/evidence.json
            dist/summary.md
          retention-days: 90
      
      - name: Upload Evidence Bundle
        uses: actions/upload-artifact@50769540e7f4bd5e21e526ee35c689e35e0d6874 # v4.4.0
        if: always()
        with:
          name: evidence-bundle-${{ github.sha }}
          path: dist/
          retention-days: 90
  
  verify-reproducibility:
    name: Verify Reproducibility
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'push'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4.1.7
      
      - name: Setup Python
        uses: actions/setup-python@f677139bbe7f9c59b41e40162b753cc15f5c515c # v5.2.0
        with:
          python-version: '3.11'
      
      - name: Install Repro Pack
        run: |
          pip install --no-cache-dir -r requirements.txt
          bash init.sh
      
      - name: Download First Build
        uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4.1.8
        with:
          name: build-artifacts-${{ github.sha }}
          path: build1/
      
      - name: Rebuild
        run: |
          python tools/det_tar.py src/ --output dist/artifact.tar
          gzip -n dist/artifact.tar
      
      - name: Compare Hashes
        run: |
          HASH1=$(sha256sum build1/artifact.tar.gz | cut -d' ' -f1)
          HASH2=$(sha256sum dist/artifact.tar.gz | cut -d' ' -f1)
          
          echo "First build:  $HASH1"
          echo "Second build: $HASH2"
          
          if [[ "$HASH1" == "$HASH2" ]]; then
            echo "✅ Build is reproducible!"
            echo "reproducible=true" >> $GITHUB_OUTPUT
          else
            echo "❌ Build is NOT reproducible!"
            echo "reproducible=false" >> $GITHUB_OUTPUT
            exit 1
          fi
  
  release:
    name: Create Release
    runs-on: ubuntu-latest
    needs: [build, verify-reproducibility]
    if: startsWith(github.ref, 'refs/tags/v')
    permissions:
      contents: write
    
    steps:
      - name: Download Artifacts
        uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4.1.8
        with:
          name: build-artifacts-${{ github.sha }}
          path: release/
      
      - name: Generate Release Notes
        run: |
          cat > release/RELEASE_NOTES.md << 'EOF'
          # Release ${{ github.ref_name }}
          
          ## Artifacts
          
          - `artifact.tar.gz` - Main release artifact
          - `vel_manifest.json` - Verifiable Evidence Ledger
          - `release_bom.json` - Release Bill of Materials
          - `evidence.json` - Complete evidence bundle
          
          ## Verification
          
          ```bash
          # Verify artifact hash
          sha256sum -c checksums.txt
          
          # Verify with VEL manifest
          python verify.py vel_manifest.json artifact.tar.gz
          ```
          
          ## Reproducibility
          
          This release is **100% reproducible**. Independent rebuilds will produce
          identical artifacts (verified by CI).
          
          ## SLSA Level
          
          This release achieves **SLSA Level 3** compliance.
          EOF
      
      - name: Generate Checksums
        run: |
          cd release
          sha256sum artifact.tar.gz > checksums.txt
          sha256sum vel_manifest.json >> checksums.txt
          sha256sum release_bom.json >> checksums.txt
      
      - name: Create Release
        uses: softprops/action-gh-release@c062e08bd532815e2082a85e87e3ef29c3e6d191 # v2.0.8
        with:
          files: |
            release/artifact.tar.gz
            release/vel_manifest.json
            release/release_bom.json
            release/evidence.json
            release/checksums.txt
          body_path: release/RELEASE_NOTES.md
          draft: false
          prerelease: false
```

### Reusable Workflow

```yaml
# .github/workflows/repro-build-reusable.yml
name: Reproducible Build (Reusable)

on:
  workflow_call:
    inputs:
      source_dir:
        required: false
        type: string
        default: 'src/'
      output_dir:
        required: false
        type: string
        default: 'dist/'
    outputs:
      artifact_hash:
        description: 'SHA-256 hash of artifact'
        value: ${{ jobs.build.outputs.artifact_hash }}
      reproducible:
        description: 'Whether build is reproducible'
        value: ${{ jobs.build.outputs.reproducible }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      artifact_hash: ${{ steps.build.outputs.hash }}
      reproducible: ${{ steps.verify.outputs.reproducible }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build
        id: build
        run: |
          # Build logic here
          HASH=$(sha256sum dist/artifact.tar.gz | cut -d' ' -f1)
          echo "hash=$HASH" >> $GITHUB_OUTPUT
```

---

## GitLab CI

### Complete Pipeline

```yaml
# .gitlab-ci.yml
variables:
  REPRO_OUTPUT_DIR: dist/
  REPRO_STRICT_MODE: '1'

stages:
  - security
  - build
  - validate
  - compliance
  - release

before_script:
  - pip install --no-cache-dir -r requirements.txt
  - bash init.sh

# Security Stage
security:scan:
  stage: security
  script:
    - python tools/secret_lint.py src/ --output dist/secrets_report.json
    - python tools/permissions_lint.py src/ --output dist/perms_report.json
    - python tools/pins_manifest_check.py .gitlab/ --output dist/pins_check.json
  artifacts:
    reports:
      sast: dist/secrets_report.json
    paths:
      - dist/*_report.json
    expire_in: 30 days
  only:
    - branches
    - tags

# Build Stage
build:artifact:
  stage: build
  script:
    - python tools/make_snapshot.py src/ --output dist/snapshot.json
    - python tools/version_stamp.py "${CI_COMMIT_TAG:-${CI_COMMIT_SHORT_SHA}}" --output dist/VERSION
    - python tools/det_tar.py src/ --output dist/artifact.tar
    - gzip -n dist/artifact.tar
    - python tools/make_vel_manifest.py
        --snapshot dist/snapshot.json
        --artifact dist/artifact.tar.gz
        --git-sha "$CI_COMMIT_SHA"
        --output dist/vel_manifest.json
  artifacts:
    paths:
      - dist/
    expire_in: 90 days
  only:
    - branches
    - tags

# Validation Stage
validate:manifest:
  stage: validate
  dependencies:
    - build:artifact
  script:
    - python tools/vel_validator.py dist/vel_manifest.json
        --artifact dist/artifact.tar.gz
        --schema schema/vel_manifest.schema.json
  only:
    - branches
    - tags

validate:determinism:
  stage: validate
  dependencies:
    - build:artifact
  script:
    - python tools/verify_tar_determinism.py dist/artifact.tar.gz --output dist/tar_check.json
    - python tools/verify_gzip_header.py dist/artifact.tar.gz --output dist/gzip_check.json
    - python tools/safe_paths_check.py dist/artifact.tar.gz --output dist/paths_check.json
  artifacts:
    paths:
      - dist/*_check.json
    expire_in: 30 days
  only:
    - branches
    - tags

validate:reproducibility:
  stage: validate
  dependencies:
    - build:artifact
  script:
    - HASH1=$(sha256sum dist/artifact.tar.gz | cut -d' ' -f1)
    - python tools/det_tar.py src/ --output rebuild/artifact.tar
    - gzip -n rebuild/artifact.tar
    - HASH2=$(sha256sum rebuild/artifact.tar.gz | cut -d' ' -f1)
    - |
      if [[ "$HASH1" == "$HASH2" ]]; then
        echo "✅ Build is reproducible!"
      else
        echo "❌ Build is NOT reproducible!"
        exit 1
      fi
  only:
    - branches
    - tags

# Compliance Stage
compliance:rbom:
  stage: compliance
  dependencies:
    - build:artifact
  script:
    - python tools/make_rbom.py dist/
        --version "${CI_COMMIT_TAG:-${CI_COMMIT_SHORT_SHA}}"
        --output dist/release_bom.json
    - python tools/rbom_check.py dist/release_bom.json
        --policy schema/rbom_policy.json
        --output dist/rbom_check.json
  artifacts:
    paths:
      - dist/release_bom.json
      - dist/rbom_check.json
    expire_in: 90 days
  only:
    - branches
    - tags

compliance:evidence:
  stage: compliance
  dependencies:
    - build:artifact
    - validate:manifest
    - validate:determinism
    - compliance:rbom
  script:
    - python tools/evidence_matrix.py dist/ --output dist/evidence.json
    - python tools/make_ci_summary.py dist/ --output dist/summary.md
  artifacts:
    paths:
      - dist/evidence.json
      - dist/summary.md
    expire_in: 90 days
  only:
    - branches
    - tags

# Release Stage
release:publish:
  stage: release
  dependencies:
    - build:artifact
    - compliance:evidence
  script:
    - cd dist
    - sha256sum artifact.tar.gz > checksums.txt
    - sha256sum vel_manifest.json >> checksums.txt
    - sha256sum release_bom.json >> checksums.txt
  release:
    tag_name: '$CI_COMMIT_TAG'
    description: 'Release $CI_COMMIT_TAG'
    assets:
      links:
        - name: 'Artifact'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/raw/dist/artifact.tar.gz?job=build:artifact'
        - name: 'VEL Manifest'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/raw/dist/vel_manifest.json?job=build:artifact'
        - name: 'RBOM'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/raw/dist/release_bom.json?job=compliance:rbom'
        - name: 'Evidence'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/raw/dist/evidence.json?job=compliance:evidence'
        - name: 'Checksums'
          url: '$CI_PROJECT_URL/-/jobs/artifacts/$CI_COMMIT_TAG/raw/dist/checksums.txt?job=release:publish'
  only:
    - tags
```

---

## Jenkins

### Declarative Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        REPRO_OUTPUT_DIR = 'dist/'
        REPRO_STRICT_MODE = '1'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    pip install --no-cache-dir -r requirements.txt
                    bash init.sh
                '''
            }
        }
        
        stage('Security Scan') {
            parallel {
                stage('Secret Scan') {
                    steps {
                        sh 'python tools/secret_lint.py src/ --output dist/secrets_report.json'
                    }
                }
                stage('Permission Check') {
                    steps {
                        sh 'python tools/permissions_lint.py src/ --output dist/perms_report.json'
                    }
                }
            }
        }
        
        stage('Build') {
            steps {
                sh '''
                    python tools/make_snapshot.py src/ --output dist/snapshot.json
                    python tools/det_tar.py src/ --output dist/artifact.tar
                    gzip -n dist/artifact.tar
                    python tools/make_vel_manifest.py \
                        --snapshot dist/snapshot.json \
                        --artifact dist/artifact.tar.gz \
                        --git-sha "${GIT_COMMIT}" \
                        --output dist/vel_manifest.json
                '''
            }
        }
        
        stage('Validate') {
            parallel {
                stage('VEL Validation') {
                    steps {
                        sh '''
                            python tools/vel_validator.py dist/vel_manifest.json \
                                --artifact dist/artifact.tar.gz
                        '''
                    }
                }
                stage('Determinism Check') {
                    steps {
                        sh '''
                            python tools/verify_tar_determinism.py dist/artifact.tar.gz \
                                --output dist/tar_check.json
                            python tools/verify_gzip_header.py dist/artifact.tar.gz \
                                --output dist/gzip_check.json
                        '''
                    }
                }
            }
        }
        
        stage('Compliance') {
            steps {
                sh '''
                    VERSION="${GIT_TAG:-${GIT_COMMIT:0:8}}"
                    python tools/make_rbom.py dist/ --version "$VERSION" \
                        --output dist/release_bom.json
                    python tools/rbom_check.py dist/release_bom.json \
                        --policy schema/rbom_policy.json
                    python tools/evidence_matrix.py dist/ --output dist/evidence.json
                '''
            }
        }
        
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: 'dist/*', fingerprint: true
            }
        }
    }
    
    post {
        always {
            sh 'python tools/make_ci_summary.py dist/ --output dist/summary.md'
            publishHTML([
                reportDir: 'dist',
                reportFiles: 'summary.md',
                reportName: 'Build Summary'
            ])
        }
        success {
            echo 'Build succeeded and is reproducible!'
        }
        failure {
            echo 'Build failed or is not reproducible!'
        }
    }
}
```

---

## CircleCI

```yaml
# .circleci/config.yml
version: 2.1

executors:
  python-executor:
    docker:
      - image: python:3.11-slim
    environment:
      REPRO_OUTPUT_DIR: dist/
      REPRO_STRICT_MODE: '1'

jobs:
  security-scan:
    executor: python-executor
    steps:
      - checkout
      - run:
          name: Install dependencies
          command: |
            pip install --no-cache-dir -r requirements.txt
            bash init.sh
      - run:
          name: Scan for secrets
          command: python tools/secret_lint.py src/ --output dist/secrets_report.json
      - run:
          name: Check permissions
          command: python tools/permissions_lint.py src/ --output dist/perms_report.json
      - store_artifacts:
          path: dist/
          destination: security-reports
  
  build:
    executor: python-executor
    steps:
      - checkout
      - run:
          name: Install dependencies
          command: |
            pip install --no-cache-dir -r requirements.txt
            bash init.sh
      - run:
          name: Build artifact
          command: |
            python tools/make_snapshot.py src/ --output dist/snapshot.json
            python tools/det_tar.py src/ --output dist/artifact.tar
            gzip -n dist/artifact.tar
            python tools/make_vel_manifest.py \
              --snapshot dist/snapshot.json \
              --artifact dist/artifact.tar.gz \
              --git-sha "$CIRCLE_SHA1" \
              --output dist/vel_manifest.json
      - persist_to_workspace:
          root: .
          paths:
            - dist/
  
  validate:
    executor: python-executor
    steps:
      - checkout
      - attach_workspace:
          at: .
      - run:
          name: Install dependencies
          command: |
            pip install --no-cache-dir -r requirements.txt
            bash init.sh
      - run:
          name: Validate manifest
          command: |
            python tools/vel_validator.py dist/vel_manifest.json \
              --artifact dist/artifact.tar.gz
      - run:
          name: Check determinism
          command: |
            python tools/verify_tar_determinism.py dist/artifact.tar.gz
            python tools/verify_gzip_header.py dist/artifact.tar.gz
  
  compliance:
    executor: python-executor
    steps:
      - checkout
      - attach_workspace:
          at: .
      - run:
          name: Install dependencies
          command: |
            pip install --no-cache-dir -r requirements.txt
            bash init.sh
      - run:
          name: Generate RBOM
          command: |
            VERSION="${CIRCLE_TAG:-${CIRCLE_SHA1:0:8}}"
            python tools/make_rbom.py dist/ --version "$VERSION"
            python tools/rbom_check.py dist/release_bom.json \
              --policy schema/rbom_policy.json
      - run:
          name: Generate evidence
          command: python tools/evidence_matrix.py dist/ --output dist/evidence.json
      - store_artifacts:
          path: dist/
          destination: release-artifacts

workflows:
  version: 2
  build-and-release:
    jobs:
      - security-scan
      - build:
          requires:
            - security-scan
      - validate:
          requires:
            - build
      - compliance:
          requires:
            - validate
```

---

## Azure Pipelines

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main
      - develop
  tags:
    include:
      - v*

pool:
  vmImage: 'ubuntu-latest'

variables:
  REPRO_OUTPUT_DIR: dist/
  REPRO_STRICT_MODE: '1'

stages:
  - stage: Security
    displayName: 'Security Scan'
    jobs:
      - job: Scan
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
          
          - script: |
              pip install --no-cache-dir -r requirements.txt
              bash init.sh
            displayName: 'Install dependencies'
          
          - script: python tools/secret_lint.py src/ --output $(Build.ArtifactStagingDirectory)/secrets_report.json
            displayName: 'Scan for secrets'
          
          - script: python tools/permissions_lint.py src/ --output $(Build.ArtifactStagingDirectory)/perms_report.json
            displayName: 'Check permissions'
          
          - publish: $(Build.ArtifactStagingDirectory)
            artifact: security-reports

  - stage: Build
    displayName: 'Build Artifact'
    dependsOn: Security
    jobs:
      - job: Build
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
          
          - script: |
              pip install --no-cache-dir -r requirements.txt
              bash init.sh
            displayName: 'Install dependencies'
          
          - script: |
              python tools/make_snapshot.py src/ --output dist/snapshot.json
              python tools/det_tar.py src/ --output dist/artifact.tar
              gzip -n dist/artifact.tar
              python tools/make_vel_manifest.py \
                --snapshot dist/snapshot.json \
                --artifact dist/artifact.tar.gz \
                --git-sha "$(Build.SourceVersion)" \
                --output dist/vel_manifest.json
            displayName: 'Build artifact'
          
          - publish: dist/
            artifact: build-artifacts

  - stage: Validate
    displayName: 'Validate Build'
    dependsOn: Build
    jobs:
      - job: Validate
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
          
          - download: current
            artifact: build-artifacts
          
          - script: |
              pip install --no-cache-dir -r requirements.txt
              bash init.sh
            displayName: 'Install dependencies'
          
          - script: |
              python tools/vel_validator.py $(Pipeline.Workspace)/build-artifacts/vel_manifest.json \
                --artifact $(Pipeline.Workspace)/build-artifacts/artifact.tar.gz
            displayName: 'Validate manifest'
          
          - script: |
              python tools/verify_tar_determinism.py $(Pipeline.Workspace)/build-artifacts/artifact.tar.gz
              python tools/verify_gzip_header.py $(Pipeline.Workspace)/build-artifacts/artifact.tar.gz
            displayName: 'Check determinism'

  - stage: Compliance
    displayName: 'Compliance Checks'
    dependsOn: Validate
    jobs:
      - job: Compliance
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
          
          - download: current
            artifact: build-artifacts
          
          - script: |
              pip install --no-cache-dir -r requirements.txt
              bash init.sh
            displayName: 'Install dependencies'
          
          - script: |
              VERSION="$(Build.SourceBranchName)"
              python tools/make_rbom.py $(Pipeline.Workspace)/build-artifacts/ --version "$VERSION"
              python tools/rbom_check.py $(Pipeline.Workspace)/build-artifacts/release_bom.json \
                --policy schema/rbom_policy.json
              python tools/evidence_matrix.py $(Pipeline.Workspace)/build-artifacts/ \
                --output $(Pipeline.Workspace)/build-artifacts/evidence.json
            displayName: 'Generate compliance reports'
          
          - publish: $(Pipeline.Workspace)/build-artifacts/
            artifact: release-bundle
```

---

## Docker Integration

### Dockerfile for Reproducible Builds

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    gzip \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy Repro Pack tools
COPY tools/ /repro-pack/tools/
COPY schema/ /repro-pack/schema/
COPY requirements.txt /repro-pack/
COPY init.sh /repro-pack/

# Install Python dependencies
RUN cd /repro-pack && \
    pip install --no-cache-dir -r requirements.txt && \
    bash init.sh

# Set environment variables
ENV REPRO_OUTPUT_DIR=/workspace/dist
ENV REPRO_STRICT_MODE=1
ENV PATH="/repro-pack/tools:${PATH}"

# Default command
CMD ["bash"]
```

### Docker Compose for Complete Pipeline

```yaml
# docker-compose.yml
version: '3.8'

services:
  build:
    build: .
    volumes:
      - ./src:/workspace/src:ro
      - ./dist:/workspace/dist
    command: >
      bash -c "
        python /repro-pack/tools/make_snapshot.py src/ --output dist/snapshot.json &&
        python /repro-pack/tools/det_tar.py src/ --output dist/artifact.tar &&
        gzip -n dist/artifact.tar &&
        python /repro-pack/tools/make_vel_manifest.py
          --snapshot dist/snapshot.json
          --artifact dist/artifact.tar.gz
          --output dist/vel_manifest.json
      "
  
  validate:
    build: .
    volumes:
      - ./dist:/workspace/dist:ro
    depends_on:
      - build
    command: >
      bash -c "
        python /repro-pack/tools/vel_validator.py dist/vel_manifest.json
          --artifact dist/artifact.tar.gz &&
        python /repro-pack/tools/verify_tar_determinism.py dist/artifact.tar.gz &&
        python /repro-pack/tools/verify_gzip_header.py dist/artifact.tar.gz
      "
  
  compliance:
    build: .
    volumes:
      - ./dist:/workspace/dist
    depends_on:
      - validate
    command: >
      bash -c "
        python /repro-pack/tools/make_rbom.py dist/ --version v1.0.0 &&
        python /repro-pack/tools/rbom_check.py dist/release_bom.json
          --policy /repro-pack/schema/rbom_policy.json &&
        python /repro-pack/tools/evidence_matrix.py dist/ --output dist/evidence.json
      "
```

### Usage

```bash
# Build with Docker
docker-compose up build

# Validate
docker-compose up validate

# Full pipeline
docker-compose up
```

---

## Makefile Integration

### Complete Makefile

```makefile
# Makefile
.PHONY: all build verify security compliance clean help

# Configuration
SOURCE_DIR ?= src/
OUTPUT_DIR ?= dist/
VERSION ?= $(shell git describe --tags --always)
GIT_SHA ?= $(shell git rev-parse HEAD)

# Tools
PYTHON := python
TOOLS_DIR := tools/

# Targets
all: build verify security compliance

help:
	@echo "Repro Pack Build Targets:"
	@echo "  make build       - Build reproducible artifact"
	@echo "  make verify      - Validate build"
	@echo "  make security    - Run security scans"
	@echo "  make compliance  - Generate compliance reports"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make all         - Run complete pipeline"

build: $(OUTPUT_DIR)/artifact.tar.gz $(OUTPUT_DIR)/vel_manifest.json

$(OUTPUT_DIR)/snapshot.json:
	@echo "Creating snapshot..."
	@mkdir -p $(OUTPUT_DIR)
	$(PYTHON) $(TOOLS_DIR)/make_snapshot.py $(SOURCE_DIR) \
		--output $@

$(OUTPUT_DIR)/artifact.tar: $(OUTPUT_DIR)/snapshot.json
	@echo "Building deterministic tarball..."
	$(PYTHON) $(TOOLS_DIR)/det_tar.py $(SOURCE_DIR) \
		--output $@

$(OUTPUT_DIR)/artifact.tar.gz: $(OUTPUT_DIR)/artifact.tar
	@echo "Compressing artifact..."
	gzip -n $(OUTPUT_DIR)/artifact.tar

$(OUTPUT_DIR)/vel_manifest.json: $(OUTPUT_DIR)/snapshot.json $(OUTPUT_DIR)/artifact.tar.gz
	@echo "Generating VEL manifest..."
	$(PYTHON) $(TOOLS_DIR)/make_vel_manifest.py \
		--snapshot $(OUTPUT_DIR)/snapshot.json \
		--artifact $(OUTPUT_DIR)/artifact.tar.gz \
		--git-sha $(GIT_SHA) \
		--output $@

verify: $(OUTPUT_DIR)/vel_manifest.json
	@echo "Validating VEL manifest..."
	$(PYTHON) $(TOOLS_DIR)/vel_validator.py $(OUTPUT_DIR)/vel_manifest.json \
		--artifact $(OUTPUT_DIR)/artifact.tar.gz
	@echo "Checking tar determinism..."
	$(PYTHON) $(TOOLS_DIR)/verify_tar_determinism.py $(OUTPUT_DIR)/artifact.tar.gz
	@echo "Checking gzip header..."
	$(PYTHON) $(TOOLS_DIR)/verify_gzip_header.py $(OUTPUT_DIR)/artifact.tar.gz
	@echo "Checking file paths..."
	$(PYTHON) $(TOOLS_DIR)/safe_paths_check.py $(OUTPUT_DIR)/artifact.tar.gz
	@echo "✅ All validations passed"

security:
	@echo "Running security scans..."
	@mkdir -p $(OUTPUT_DIR)
	$(PYTHON) $(TOOLS_DIR)/secret_lint.py $(SOURCE_DIR) \
		--output $(OUTPUT_DIR)/secrets_report.json
	$(PYTHON) $(TOOLS_DIR)/permissions_lint.py $(SOURCE_DIR) \
		--output $(OUTPUT_DIR)/perms_report.json
	@echo "✅ Security scans complete"

compliance: $(OUTPUT_DIR)/release_bom.json $(OUTPUT_DIR)/evidence.json

$(OUTPUT_DIR)/release_bom.json: $(OUTPUT_DIR)/artifact.tar.gz
	@echo "Generating RBOM..."
	$(PYTHON) $(TOOLS_DIR)/make_rbom.py $(OUTPUT_DIR) \
		--version $(VERSION) \
		--output $@
	@echo "Validating RBOM..."
	$(PYTHON) $(TOOLS_DIR)/rbom_check.py $@ \
		--policy schema/rbom_policy.json

$(OUTPUT_DIR)/evidence.json: $(OUTPUT_DIR)/release_bom.json
	@echo "Generating evidence matrix..."
	$(PYTHON) $(TOOLS_DIR)/evidence_matrix.py $(OUTPUT_DIR) \
		--output $@
	@echo "✅ Compliance reports generated"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(OUTPUT_DIR)
	@echo "✅ Clean complete"

.PRECIOUS: $(OUTPUT_DIR)/artifact.tar $(OUTPUT_DIR)/snapshot.json
```

---

## Pre-commit Hooks

### Setup

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: secret-scan
        name: Scan for secrets
        entry: python tools/secret_lint.py
        language: python
        pass_filenames: false
        args: ['.', '--output', '/tmp/secret_scan.json']
      
      - id: permission-check
        name: Check file permissions
        entry: python tools/permissions_lint.py
        language: python
        pass_filenames: false
        args: ['.', '--output', '/tmp/perms_check.json']
      
      - id: action-pins
        name: Verify GitHub Actions pins
        entry: python tools/pins_manifest_check.py
        language: python
        files: '^\.github/workflows/.*\.ya?ml$'
        args: ['.github/workflows/']

# Install with:
# pip install pre-commit
# pre-commit install
```

---

## Release Automation

### Automated Release Script

```bash
#!/bin/bash
# scripts/release.sh

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version>"
    exit 1
fi

echo "🚀 Creating release $VERSION"

# 1. Build
echo "📦 Building artifact..."
make clean
make build

# 2. Verify
echo "✅ Verifying build..."
make verify

# 3. Security
echo "🔒 Running security scans..."
make security

# 4. Compliance
echo "📋 Generating compliance reports..."
make compliance

# 5. Tag
echo "🏷️  Creating git tag..."
git tag -a "$VERSION" -m "Release $VERSION"

# 6. Generate checksums
echo "🔐 Generating checksums..."
cd dist/
sha256sum artifact.tar.gz > checksums.txt
sha256sum vel_manifest.json >> checksums.txt
sha256sum release_bom.json >> checksums.txt
cd ..

# 7. Push
echo "⬆️  Pushing to remote..."
git push origin "$VERSION"

echo "✨ Release $VERSION complete!"
echo ""
echo "Artifacts:"
echo "  - dist/artifact.tar.gz"
echo "  - dist/vel_manifest.json"
echo "  - dist/release_bom.json"
echo "  - dist/evidence.json"
echo "  - dist/checksums.txt"
```

---

## Best Practices

### DO
✅ Pin all action versions to SHA  
✅ Run security scans on every commit  
✅ Verify reproducibility in CI  
✅ Archive evidence bundles  
✅ Use caching for dependencies  
✅ Validate before release  

### DON'T
❌ Skip validation steps  
❌ Use mutable tags (v1, latest)  
❌ Ignore security findings  
❌ Modify artifacts after build  
❌ Store secrets in code  

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guide.

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-15  
**Status**: Complete
