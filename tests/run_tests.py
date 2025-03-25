#!/usr/bin/env python
"""
Test runner for Spectral Agent project.

This script provides an easy way to run tests with different configurations.
It serves as a simple wrapper around pytest with common options.
"""

import sys
import subprocess
import argparse
import importlib.util
import os
from pathlib import Path


def check_dependency(package_name):
    """Check if a dependency is installed."""
    return importlib.util.find_spec(package_name) is not None


def install_test_dependencies():
    """Install all required test dependencies."""
    # Get the absolute path to the requirements-test.txt file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    req_file = os.path.join(script_dir, "requirements-test.txt")
    
    if not os.path.exists(req_file):
        print(f"Error: Test requirements file not found at {req_file}")
        return False
    
    print(f"Installing test dependencies from {req_file}...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], check=True)
        print("Test dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False


def ensure_test_dirs_exist():
    """Ensure the test directories exist and have __init__.py files."""
    test_root = Path(__file__).parent
    unit_dir = test_root / "unit"
    integration_dir = test_root / "integration"
    
    # Check if directories exist
    if not unit_dir.exists():
        os.makedirs(unit_dir, exist_ok=True)
        print(f"Created directory: {unit_dir}")
    
    if not integration_dir.exists():
        os.makedirs(integration_dir, exist_ok=True)
        print(f"Created directory: {integration_dir}")
    
    # Ensure __init__.py files exist
    unit_init = unit_dir / "__init__.py"
    if not unit_init.exists():
        with open(unit_init, 'w') as f:
            f.write('"""Unit tests for Spectral Agent."""\n')
        print(f"Created __init__.py in {unit_dir}")
    
    integration_init = integration_dir / "__init__.py"
    if not integration_init.exists():
        with open(integration_init, 'w') as f:
            f.write('"""Integration tests for Spectral Agent."""\n')
        print(f"Created __init__.py in {integration_dir}")
    
    # Ensure root __init__.py exists
    root_init = test_root / "__init__.py"
    if not root_init.exists():
        with open(root_init, 'w') as f:
            f.write('"""Test suite for Spectral Agent."""\n')
        print(f"Created __init__.py in {test_root}")


def main():
    """Run the test suite with specified options."""
    parser = argparse.ArgumentParser(description="Run Spectral Agent tests")
    
    parser.add_argument(
        "--unit", action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", 
        help="Enable verbose output"
    )
    parser.add_argument(
        "--coverage", action="store_true", 
        help="Generate coverage report"
    )
    parser.add_argument(
        "--html-report", action="store_true", 
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--tests", nargs="*", 
        help="Specific test modules to run (e.g. test_twitter_sentiment)"
    )
    parser.add_argument(
        "--install-deps", action="store_true",
        help="Install test dependencies before running tests"
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Set up test environment (create directories and __init__.py files)"
    )
    
    args = parser.parse_args()
    
    # Set up test environment if requested
    if args.setup:
        ensure_test_dirs_exist()
        print("Test environment set up successfully.")
        
    # Install dependencies if requested
    if args.install_deps:
        if not install_test_dependencies():
            return 1
    
    # Check for pytest
    if not check_dependency("pytest"):
        print("\nERROR: pytest is not installed. Please install it with:")
        print("pip install pytest")
        print("Or run this script with the --install-deps flag\n")
        return 1
    
    # Get the path to test directory
    test_dir = Path(__file__).parent.absolute()
    
    # Base command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add verbosity flag
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage options
    if args.coverage or args.html_report:
        # Check if pytest-cov is installed
        if not check_dependency("pytest_cov"):
            print("\nERROR: pytest-cov is not installed but is required for coverage reports.")
            print("Please install it with:")
            print("pip install pytest-cov")
            print("Or run this script with the --install-deps flag\n")
            return 1
            
        cmd.append("--cov=src")
        
        if args.html_report:
            cmd.append("--cov-report=html")
        elif args.coverage:
            cmd.append("--cov-report=term")
    
    # Determine which tests to run
    if args.unit:
        cmd.append(str(test_dir / "unit"))
    elif args.integration:
        cmd.append(str(test_dir / "integration"))
    elif args.tests:
        for test in args.tests:
            if not test.startswith("test_"):
                test = f"test_{test}"
            # Look for the test in both unit and integration directories
            unit_test = test_dir / "unit" / f"{test}.py"
            integration_test = test_dir / "integration" / f"{test}.py"
            
            if unit_test.exists():
                cmd.append(str(unit_test))
            if integration_test.exists():
                cmd.append(str(integration_test))
    else:
        # Run all tests
        cmd.append(str(test_dir))
    
    # Print command being run
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        # Run the tests
        result = subprocess.run(cmd)
        return result.returncode
    except Exception as e:
        print(f"\nError running tests: {e}")
        print(f"\nCommand was: {' '.join(cmd)}\n")
        return 1
    

if __name__ == "__main__":
    sys.exit(main()) 