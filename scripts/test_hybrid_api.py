#!/usr/bin/env python3
"""
Test script for Hybrid Query API endpoints.

Usage:
    python3 scripts/test_hybrid_api.py [--url http://localhost:8080]
"""

import requests
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


class HybridAPITester:
    """Test Hybrid Query API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.results = []
        self.passed = 0
        self.failed = 0

    def print_header(self, text: str):
        """Print section header."""
        print(f"\n{Colors.BLUE}{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}{Colors.RESET}\n")

    def test_endpoint(self, name: str, method: str, endpoint: str,
                     data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> bool:
        """Test a single endpoint."""
        url = f"{self.base_url}{endpoint}"

        try:
            print(f"  📍 {name}")
            print(f"     {method} {endpoint}")

            if method == "GET":
                response = requests.get(url, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code in [200, 201]:
                print(f"     {Colors.GREEN}✓ Status: {response.status_code}{Colors.RESET}")
                result = response.json()

                # Print key fields
                if isinstance(result, dict):
                    if "status" in result:
                        print(f"     Status: {result['status']}")
                    if "count" in result:
                        print(f"     Count: {result['count']}")
                    if "query_type" in result:
                        print(f"     Query Type: {result['query_type']}")

                self.passed += 1
                self.results.append((name, True, f"Status {response.status_code}"))
                return True
            else:
                print(f"     {Colors.RED}✗ Status: {response.status_code}{Colors.RESET}")
                print(f"     Response: {response.text[:200]}")
                self.failed += 1
                self.results.append((name, False, f"Status {response.status_code}"))
                return False

        except requests.ConnectionError:
            print(f"     {Colors.RED}✗ Connection refused - API not running?{Colors.RESET}")
            self.failed += 1
            self.results.append((name, False, "Connection refused"))
            return False
        except Exception as e:
            print(f"     {Colors.RED}✗ Error: {str(e)}{Colors.RESET}")
            self.failed += 1
            self.results.append((name, False, str(e)))
            return False

    def run_tests(self):
        """Run all API tests."""
        self.print_header("🔗 HYBRID QUERY API TEST SUITE")

        # Test 1: Health check
        self.print_header("1. Health Check")
        self.test_endpoint(
            "Health Check",
            "GET",
            "/api/v1/hybrid/health"
        )

        # Test 2: Clinic operations
        self.print_header("2. Clinic Operations (Database)")

        self.test_endpoint(
            "Get Clinic Schedule - Monday",
            "GET",
            "/api/v1/hybrid/clinic/schedule",
            params={"day": "星期一"}
        )

        self.test_endpoint(
            "Get Clinic Staff",
            "GET",
            "/api/v1/hybrid/clinic/staff"
        )

        self.test_endpoint(
            "Get Clinic Staff - Doctors Only",
            "GET",
            "/api/v1/hybrid/clinic/staff",
            params={"position": "主治醫師"}
        )

        self.test_endpoint(
            "Get Clinic Supplies",
            "GET",
            "/api/v1/hybrid/clinic/supplies"
        )

        self.test_endpoint(
            "Get Clinic Supplies - Low Stock",
            "GET",
            "/api/v1/hybrid/clinic/supplies",
            params={"status": "LOW_STOCK"}
        )

        # Test 3: Medical knowledge
        self.print_header("3. Medical Knowledge (RAG)")

        self.test_endpoint(
            "Search Medical Knowledge",
            "POST",
            "/api/v1/hybrid/medical/search",
            data={"query": "糖尿病原因", "top_k": 3}
        )

        self.test_endpoint(
            "Search Medical Condition",
            "POST",
            "/api/v1/hybrid/medical/condition",
            data={"condition": "糖尿病"}
        )

        self.test_endpoint(
            "Search Medical Condition - High BP",
            "POST",
            "/api/v1/hybrid/medical/condition",
            data={"condition": "高血壓"}
        )

        # Test 4: Hybrid queries
        self.print_header("4. Hybrid Queries (Combined)")

        self.test_endpoint(
            "Diagnostic Query - Symptoms",
            "POST",
            "/api/v1/hybrid/diagnostic",
            data={"symptoms": "多渴、多尿、疲勞"}
        )

        self.test_endpoint(
            "Diagnostic Query - Different Symptoms",
            "POST",
            "/api/v1/hybrid/diagnostic",
            data={"symptoms": "頭痛、胸悶"}
        )

        self.test_endpoint(
            "Intelligent Query - Clinic Operation",
            "POST",
            "/api/v1/hybrid/query",
            data={"query": "What time is the clinic open on Monday?"}
        )

        self.test_endpoint(
            "Intelligent Query - Medical Knowledge",
            "POST",
            "/api/v1/hybrid/query",
            data={"query": "What causes diabetes?"}
        )

        self.test_endpoint(
            "Intelligent Query - Hybrid",
            "POST",
            "/api/v1/hybrid/query",
            data={"query": "Can Dr. Wang treat my diabetes?"}
        )

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        self.print_header("📊 TEST SUMMARY")

        print(f"Total Tests: {self.passed + self.failed}")
        print(f"{Colors.GREEN}✓ Passed: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}✗ Failed: {self.failed}{Colors.RESET}\n")

        if self.failed > 0:
            print("Failed Tests:")
            for name, status, msg in self.results:
                if not status:
                    print(f"  {Colors.RED}✗{Colors.RESET} {name}: {msg}")

        if self.passed == len(self.results):
            print(f"\n{Colors.GREEN}🎉 All tests passed!{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Check the API server.{Colors.RESET}")

        print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description='Test Hybrid Query API')
    parser.add_argument('--url', default='http://localhost:8080',
                       help='API base URL (default: http://localhost:8080)')
    parser.add_argument('--verbose', action='store_true',
                       help='Print detailed response JSON')

    args = parser.parse_args()

    print(f"\n{Colors.BLUE}🔗 Hybrid Query API Tester{Colors.RESET}")
    print(f"Target: {args.url}\n")

    tester = HybridAPITester(base_url=args.url)
    tester.run_tests()


if __name__ == '__main__':
    main()
