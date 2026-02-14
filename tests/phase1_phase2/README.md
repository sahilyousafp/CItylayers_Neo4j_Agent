# Phase 1 & 2 Testing

This folder contains test documentation and test cases for:
- **Phase 1**: Multi-Dataset LLM Integration
- **Phase 2**: Context-Based Comment Selection

## Test Structure

```
tests/phase1_phase2/
├── README.md (this file)
├── TESTING_GUIDE.md (Main testing procedures)
├── test_single_dataset/
│   └── Test scenarios for CityLayers-only queries
├── test_multi_dataset/
│   ├── test_weather/
│   ├── test_transport/
│   ├── test_vegetation/
│   └── test_all_combined/
├── test_comment_relevance/
│   └── Comment scoring validation tests
└── test_results/
    └── Test execution results and logs
```

## Quick Links

- [Main Testing Guide](TESTING_GUIDE.md) - Comprehensive test procedures
- [Test Results Template](test_results/TEMPLATE.md) - For documenting test runs

## Testing Status

- [ ] Phase 1: Multi-Dataset Integration
- [ ] Phase 2: Comment Relevance
- [ ] Performance Testing
- [ ] Regression Testing

## How to Run Tests

1. Checkout the feature branch:
   ```bash
   git checkout feature/multi-dataset-llm-pdf-export
   ```

2. Start the application:
   ```bash
   python app.py
   ```

3. Follow scenarios in [TESTING_GUIDE.md](TESTING_GUIDE.md)

4. Document results in `test_results/` folder
