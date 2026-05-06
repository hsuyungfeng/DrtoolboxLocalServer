"""
End-to-End RAG Test Suite

Tests the complete RAG pipeline from API to LLM generation.
Validates the "truths" from PLAN.md:
- 端到端 RAG 查詢運作正常
- 模型延遲 <200ms
- Relevance > 0.7
- 24 小時穩定運作 (simulated via repeated queries)

Usage:
    python tests/e2e_rag_test.py

Requirements:
    - Flask server running on http://localhost:5000 (or set SERVER_URL env)
    - Documents ingested into Chroma collection
    - LLM model loaded and available
"""

import os
import sys
import time
import json
import logging
import unittest
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Configuration
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5000")
API_BASE = f"{SERVER_URL}/api/v1"
HEALTH_ENDPOINT = f"{SERVER_URL}/health"
RAG_QUERY_ENDPOINT = f"{API_BASE}/rag/query"


@dataclass
class TestResult:
    """Test result data class."""
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class E2ERAGTester:
    """
    End-to-End RAG Testing Suite
    
    Tests:
    1. Health check
    2. RAG query functionality
    3. Response format (answer, confidence, citations)
    4. Latency < 200ms
    5. Relevance > 0.7
    6. Stability (multiple queries)
    """
    
    def __init__(self, server_url: str = SERVER_URL):
        self.server_url = server_url
        self.results: List[TestResult] = []
        self.test_queries = [
            "糖尿病的治療方式是什麼？",
            "高血壓的診斷標準",
            "心臟病的預防方法",
            "感冒的症狀和治療",
            "頭痛的成因與處理",
        ]
    
    def run_all_tests(self) -> bool:
        """Run all E2E tests and return overall pass/fail."""
        logger.info("=" * 60)
        logger.info("Starting E2E RAG Test Suite")
        logger.info("=" * 60)
        
        # Test 1: Health Check
        self._test_health_check()
        
        # Test 2: RAG Query - Basic
        self._test_rag_query_basic()
        
        # Test 3: Response Format
        self._test_response_format()
        
        # Test 4: Latency
        self._test_latency()
        
        # Test 5: Relevance
        self._test_relevance()
        
        # Test 6: Stability
        self._test_stability()
        
        # Print summary
        self._print_summary()
        
        # Return True if all passed
        return all(r.passed for r in self.results)
    
    def _test_health_check(self):
        """Test 1: Health endpoint responds correctly."""
        logger.info("\n[Test 1] Testing health endpoint...")
        
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "healthy":
                    self.results.append(TestResult(
                        passed=True,
                        message="Health check passed",
                        details=data
                    ))
                    logger.info("✓ Health check passed")
                    return
            
            self.results.append(TestResult(
                passed=False,
                message=f"Health check failed: {response.status_code}",
                details=response.json() if response.content else None
            ))
            logger.error("✗ Health check failed")
            
        except Exception as e:
            self.results.append(TestResult(
                passed=False,
                message=f"Health check error: {str(e)}"
            ))
            logger.error(f"✗ Health check error: {e}")
    
    def _test_rag_query_basic(self):
        """Test 2: Basic RAG query returns valid response."""
        logger.info("\n[Test 2] Testing basic RAG query...")
        
        try:
            payload = {
                "prompt": self.test_queries[0],
                "n_results": 5
            }
            
            response = requests.post(
                RAG_QUERY_ENDPOINT,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "answer" in data:
                    self.results.append(TestResult(
                        passed=True,
                        message="RAG query successful",
                        details={"answer_length": len(data.get("answer", ""))}
                    ))
                    logger.info(f"✓ RAG query returned answer ({len(data.get('answer', ''))} chars)")
                    return
            
            self.results.append(TestResult(
                passed=False,
                message=f"RAG query failed: {response.status_code}",
                details=response.json() if response.content else None
            ))
            logger.error("✗ RAG query failed")
            
        except Exception as e:
            self.results.append(TestResult(
                passed=False,
                message=f"RAG query error: {str(e)}"
            ))
            logger.error(f"✗ RAG query error: {e}")
    
    def _test_response_format(self):
        """Test 3: Response contains required fields."""
        logger.info("\n[Test 3] Testing response format...")
        
        try:
            payload = {
                "prompt": self.test_queries[0],
                "n_results": 5
            }
            
            response = requests.post(
                RAG_QUERY_ENDPOINT,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                self.results.append(TestResult(
                    passed=False,
                    message="Response format test failed (API error)"
                ))
                return
            
            data = response.json()
            
            # Check required fields
            required_fields = ["answer", "confidence"]
            missing_fields = [f for f in required_fields if f not in data]
            
            # Check citations if present
            has_citations = "citations" in data and len(data.get("citations", [])) > 0
            
            if not missing_fields:
                confidence = data.get("confidence", 0)
                
                self.results.append(TestResult(
                    passed=True,
                    message=f"Response format valid, confidence={confidence:.3f}",
                    details={
                        "fields": list(data.keys()),
                        "citations_count": len(data.get("citations", []))
                    }
                ))
                logger.info(f"✓ Response format valid (confidence: {confidence:.3f}, citations: {len(data.get('citations', []))})")
                return
            
            self.results.append(TestResult(
                passed=False,
                message=f"Missing fields: {missing_fields}",
                details={"received_fields": list(data.keys())}
            ))
            logger.error(f"✗ Missing fields: {missing_fields}")
            
        except Exception as e:
            self.results.append(TestResult(
                passed=False,
                message=f"Response format error: {str(e)}"
            ))
            logger.error(f"✗ Response format error: {e}")
    
    def _test_latency(self):
        """Test 4: Model latency < 200ms."""
        logger.info("\n[Test 4] Testing latency...")
        
        try:
            latencies = []
            
            for i, query in enumerate(self.test_queries[:3]):  # Test with 3 queries
                payload = {"prompt": query, "n_results": 5}
                
                start_time = time.time()
                response = requests.post(RAG_QUERY_ENDPOINT, json=payload, timeout=30)
                elapsed_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    latencies.append(elapsed_ms)
                    logger.info(f"  Query {i+1}: {elapsed_ms:.1f}ms")
            
            if not latencies:
                self.results.append(TestResult(
                    passed=False,
                    message="No successful queries for latency test"
                ))
                return
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            passed = max_latency < 200
            
            self.results.append(TestResult(
                passed=passed,
                message=f"Latency test: avg={avg_latency:.1f}ms, max={max_latency:.1f}ms",
                details={
                    "avg_latency_ms": avg_latency,
                    "max_latency_ms": max_latency,
                    "threshold_ms": 200
                }
            ))
            
            if passed:
                logger.info(f"✓ Latency test passed (max: {max_latency:.1f}ms < 200ms)")
            else:
                logger.error(f"✗ Latency test failed (max: {max_latency:.1f}ms >= 200ms)")
            
        except Exception as e:
            self.results.append(TestResult(
                passed=False,
                message=f"Latency test error: {str(e)}"
            ))
            logger.error(f"✗ Latency test error: {e}")
    
    def _test_relevance(self):
        """Test 5: Relevance > 0.7 for retrieved chunks."""
        logger.info("\n[Test 5] Testing relevance...")
        
        try:
            payload = {
                "prompt": self.test_queries[0],
                "n_results": 5
            }
            
            response = requests.post(
                RAG_QUERY_ENDPOINT,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                self.results.append(TestResult(
                    passed=False,
                    message="Relevance test failed (API error)"
                ))
                return
            
            data = response.json()
            citations = data.get("citations", [])
            
            if not citations:
                # Try to get relevance from search endpoint
                search_payload = {"query": self.test_queries[0], "n_results": 5}
                search_response = requests.post(
                    f"{API_BASE}/rag/search",
                    json=search_payload,
                    timeout=30
                )
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    results = search_data.get("results", [])
                    
                    if results:
                        relevances = [r.get("relevance", 0) for r in results if "relevance" in r]
                        if relevances:
                            avg_relevance = sum(relevances) / len(relevances)
                            passed = avg_relevance > 0.7
                            
                            self.results.append(TestResult(
                                passed=passed,
                                message=f"Relevance: avg={avg_relevance:.3f}",
                                details={
                                    "avg_relevance": avg_relevance,
                                    "threshold": 0.7,
                                    "relevances": relevances
                                }
                            ))
                            
                            if passed:
                                logger.info(f"✓ Relevance test passed ({avg_relevance:.3f} > 0.7)")
                            else:
                                logger.error(f"✗ Relevance test failed ({avg_relevance:.3f} <= 0.7)")
                            return
                
                self.results.append(TestResult(
                    passed=False,
                    message="No relevance data available"
                ))
                return
            
            # Check confidence as proxy for relevance
            confidence = data.get("confidence", 0)
            passed = confidence > 0.7
            
            self.results.append(TestResult(
                passed=passed,
                message=f"Confidence (proxy for relevance): {confidence:.3f}",
                details={
                    "confidence": confidence,
                    "threshold": 0.7
                }
            ))
            
            if passed:
                logger.info(f"✓ Relevance test passed (confidence: {confidence:.3f} > 0.7)")
            else:
                logger.error(f"✗ Relevance test failed (confidence: {confidence:.3f} <= 0.7)")
            
        except Exception as e:
            self.results.append(TestResult(
                passed=False,
                message=f"Relevance test error: {str(e)}"
            ))
            logger.error(f"✗ Relevance test error: {e}")
    
    def _test_stability(self):
        """Test 6: Stability - multiple queries without failure."""
        logger.info("\n[Test 6] Testing stability...")
        
        try:
            success_count = 0
            total_queries = 5
            
            for i in range(total_queries):
                query = self.test_queries[i % len(self.test_queries)]
                payload = {"prompt": query, "n_results": 3}
                
                try:
                    response = requests.post(
                        RAG_QUERY_ENDPOINT,
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        success_count += 1
                        logger.info(f"  Query {i+1}/{total_queries}: OK")
                    else:
                        logger.warning(f"  Query {i+1}/{total_queries}: Failed ({response.status_code})")
                        
                except Exception as e:
                    logger.warning(f"  Query {i+1}/{total_queries}: Error ({e})")
                
                # Small delay between queries
                time.sleep(0.1)
            
            passed = success_count == total_queries
            
            self.results.append(TestResult(
                passed=passed,
                message=f"Stability: {success_count}/{total_queries} queries successful",
                details={
                    "success_count": success_count,
                    "total_queries": total_queries
                }
            ))
            
            if passed:
                logger.info(f"✓ Stability test passed ({success_count}/{total_queries})")
            else:
                logger.error(f"✗ Stability test failed ({success_count}/{total_queries})")
            
        except Exception as e:
            self.results.append(TestResult(
                passed=False,
                message=f"Stability test error: {str(e)}"
            ))
            logger.error(f"✗ Stability test error: {e}")
    
    def _print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        
        for i, result in enumerate(self.results, 1):
            status = "✓ PASS" if result.passed else "✗ FAIL"
            logger.info(f"  {i}. {status}: {result.message}")
        
        logger.info("-" * 60)
        logger.info(f"Total: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            logger.info("\n🎉 All tests PASSED!")
        else:
            logger.info("\n⚠️ Some tests FAILED!")
        
        logger.info("=" * 60)


def main():
    """Main entry point for E2E tests."""
    print("\n" + "=" * 60)
    print("E2E RAG Test Suite")
    print("Server:", SERVER_URL)
    print("=" * 60 + "\n")
    
    # Check if server is reachable first
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code != 200:
            print(f"ERROR: Server not healthy (status {response.status_code})")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to server at {SERVER_URL}")
        print("Please ensure the Flask server is running:")
        print(f"  python -m src.api.app")
        print(f"  (or set SERVER_URL environment variable)")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    # Run tests
    tester = E2ERAGTester()
    all_passed = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()