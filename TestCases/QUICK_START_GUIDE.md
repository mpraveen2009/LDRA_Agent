# Quick Start Guide - Running LDRA TBrun Tests

## Overview
This guide shows how to execute the end-to-end test coverage created for the math_utils and string_utils C libraries.

---

## Test Files Available

| File | Functions | Test Cases | Purpose |
|------|-----------|-----------|---------|
| `math_utils_tests.tcf` | 10 | 26 | Math operations with boundary/error cases |
| `string_utils_tests.tcf` | 8 | 25 | String operations with NULL handling |

---

## Prerequisites

1. LDRA TBrun installed at: `C:\LDRA_Toolsuite_C_CPP_10.3.0`
2. LDRA Workarea at: `C:\LDRA_Workarea_C_CPP_10.3.0`
3. Source files in: `samples/math_utils.c` and `samples/string_utils.c`
4. Test files in: `TestCases/math_utils_tests.tcf` and `TestCases/string_utils_tests.tcf`

---

## Step-by-Step Execution

### Step 1: Run Static Analysis
Instrument the source code for coverage measurement:

```python
from server import run_static_analysis

result = run_static_analysis("project_set.tcf")
print(f"Exit Code: {result['exit_code']}")
print(f"Status: {result['meaning']}")
```

**Expected**: exit_code = 0 (Pass)

---

### Step 2: Record Mode - Establish Baseline
Record expected values from the first test run:

```python
from server import run_tbrun

# Test math_utils functions
math_result = run_tbrun(
    "project_set.tcf",
    "TestCases/math_utils_tests.tcf",
    mode="record"
)
print(f"Math Tests Record Mode - Exit Code: {math_result['exit_code']}")

# Test string_utils functions
string_result = run_tbrun(
    "project_set.tcf",
    "TestCases/string_utils_tests.tcf",
    mode="record"
)
print(f"String Tests Record Mode - Exit Code: {string_result['exit_code']}")
```

**Expected**: exit_code = 0 (Pass)  
**Action**: This records the baseline expected values for all test cases

---

### Step 3: Regression Mode - Validate Tests
Run tests against recorded baseline:

```python
from server import run_tbrun

# Test math_utils functions
math_result = run_tbrun(
    "project_set.tcf",
    "TestCases/math_utils_tests.tcf",
    mode="regress"
)
print(f"Math Tests Regress Mode - Exit Code: {math_result['exit_code']}")
if math_result['exit_code'] == 0:
    print("✓ All math tests PASSED")
else:
    print(f"✗ Math tests FAILED - {math_result['meaning']}")

# Test string_utils functions
string_result = run_tbrun(
    "project_set.tcf",
    "TestCases/string_utils_tests.tcf",
    mode="regress"
)
print(f"String Tests Regress Mode - Exit Code: {string_result['exit_code']}")
if string_result['exit_code'] == 0:
    print("✓ All string tests PASSED")
else:
    print(f"✗ String tests FAILED - {string_result['meaning']}")
```

**Expected**: exit_code = 0 (Pass for all tests)  
**Exit Codes**:
- `0` = Pass (all tests successful)
- `90` = Regression failure (test output mismatch)
- `93` = Timeout (execution exceeded time limit)

---

### Step 4: Check Coverage Results
Measure code coverage achieved:

```python
from server import read_coverage_results

# For math_utils
coverage = read_coverage_results("math_utils")
print("Math Utils Coverage:")
print(coverage)

# For string_utils
coverage = read_coverage_results("string_utils")
print("\nString Utils Coverage:")
print(coverage)
```

**Output**: Coverage summary with:
- Statement Coverage (SC)
- Branch Coverage (DC)
- MC/DC Coverage

---

## Automation Example

Here's a complete test execution script:

```python
#!/usr/bin/env python3
"""
Complete test execution workflow for LDRA TBrun tests
"""

from server import (
    run_static_analysis,
    run_tbrun,
    read_coverage_results,
)
import json
from datetime import datetime

def run_full_test_suite():
    """Execute full test suite and generate report"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "coverage": {}
    }
    
    # Test files and their names
    test_files = [
        ("TestCases/math_utils_tests.tcf", "math_utils"),
        ("TestCases/string_utils_tests.tcf", "string_utils"),
    ]
    
    print("=" * 60)
    print("LDRA TBrun Automated Test Suite")
    print("=" * 60)
    
    # Step 1: Static Analysis
    print("\n[1/4] Running Static Analysis...")
    analysis = run_static_analysis("project_set.tcf")
    if analysis['exit_code'] != 0:
        print(f"✗ Static Analysis FAILED: {analysis['meaning']}")
        return report
    print("✓ Static Analysis completed")
    
    # Step 2: Record Mode
    print("\n[2/4] Recording Baseline (Record Mode)...")
    for tcf_file, test_name in test_files:
        result = run_tbrun("project_set.tcf", tcf_file, mode="record")
        status = "PASS" if result['exit_code'] == 0 else "FAIL"
        print(f"  • {test_name}: {status}")
        report["tests"][f"{test_name}_record"] = result
    
    # Step 3: Regression Mode
    print("\n[3/4] Running Regression Tests (Regress Mode)...")
    for tcf_file, test_name in test_files:
        result = run_tbrun("project_set.tcf", tcf_file, mode="regress")
        status = "PASS" if result['exit_code'] == 0 else "FAIL"
        print(f"  • {test_name}: {status}")
        if result['exit_code'] != 0:
            print(f"    → {result['meaning']}")
        report["tests"][f"{test_name}_regress"] = result
    
    # Step 4: Coverage Analysis
    print("\n[4/4] Analyzing Coverage...")
    for tcf_file, test_name in test_files:
        coverage = read_coverage_results(test_name)
        report["coverage"][test_name] = coverage
        print(f"  • {test_name}: Coverage data retrieved")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Execution Complete")
    print("=" * 60)
    print(f"\nReport saved to: test_report.json")
    
    # Save report
    with open("test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    return report

if __name__ == "__main__":
    run_full_test_suite()
```

---

## Expected Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Pass | Tests successful ✓ |
| 64 | Invalid command line | Check tool arguments |
| 81 | Instrumentation failed | Check source file syntax |
| 84 | Build failed | Verify C code compiles |
| 90 | Regression failure | Test output differs from baseline |
| 93 | Timeout | Increase timeout or optimize code |
| 103 | Licensing error | Check LDRA license |

---

## Test Case Verification

### Math Utils Test Cases (26 total)
- ✓ add: 3 cases (normal, zero, negative)
- ✓ subtract: 2 cases (normal, negative result)
- ✓ multiply: 2 cases (normal, by zero)
- ✓ divide: 2 cases (normal, by zero error)
- ✓ absolute_value: 3 cases (positive, negative, zero)
- ✓ max: 3 cases (a>b, b>a, equal)
- ✓ min: 1 case (a<b)
- ✓ clamp: 4 cases (within, below, above, error)
- ✓ is_even: 3 cases (even, odd, zero)
- ✓ power: 3 cases (normal, base case, error)

### String Utils Test Cases (25 total)
- ✓ string_length: 3 cases (normal, empty, NULL)
- ✓ string_compare: 4 cases (equal, less, greater, NULL)
- ✓ char_is_digit: 4 cases (digit, non-digit, '0', '9')
- ✓ char_is_alpha: 3 cases (lower, upper, digit)
- ✓ char_to_upper: 3 cases (lower→upper, upper, non-letter)
- ✓ char_to_lower: 2 cases (upper→lower, lower)
- ✓ string_index_of: 3 cases (found, not found, NULL)
- ✓ string_last_index_of: 3 cases (found, not found, NULL)

---

## Troubleshooting

### Issue: "File not found" errors
- Verify paths are absolute
- Check LDRA installation directory
- Ensure source files exist in `samples/` folder

### Issue: Build failures (exit code 84)
- Check C syntax in source files
- Verify all includes are available
- Try compiling with GCC first

### Issue: Coverage not found
- Run tests in record mode first
- Check workarea exists at `C:\LDRA_Workarea_C_CPP_10.3.0`
- Wait for execution history files to be written

### Issue: Tests timeout (exit code 93)
- Increase timeout in `run_tbrun()` parameters
- Check for infinite loops in test code
- Run smaller test batches

---

## Coverage Goals

| Metric | Target | Current |
|--------|--------|---------|
| Statement Coverage (SC) | ≥ 90% | To be measured |
| Branch Coverage (DC) | ≥ 85% | To be measured |
| MC/DC Coverage | ≥ 80% | To be measured |

---

## Additional Resources

- [LDRA TBrun Documentation](https://www.ldra.com)
- [TCF File Format Reference](TestCases/TEST_COVERAGE_REPORT.md)
- [Test Case Design Guide](TestCases/TEST_COVERAGE_REPORT.md#test-coverage-summary)
