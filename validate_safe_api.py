#!/usr/bin/env python3
"""
Safe API Migration Validation Script

This script validates that the new Safe Transaction Service API integration is working correctly.
It tests authentication, chain resolution, and basic API connectivity.
"""

import os
import sys
from brownie_safe import SafeTransactionServiceConfig, SafeTransactionServiceClient, ApiError


def validate_config():
    """Validate environment configuration."""
    print("🔧 Validating configuration...")
    
    config = SafeTransactionServiceConfig()
    
    print(f"  Base URL: {config.base_url}")
    print(f"  Timeout: {config.timeout}s")
    print(f"  Retries: {config.retries}")
    print(f"  API Key: {'✓ Set' if config.api_key else '✗ Not set'}")
    print(f"  Allow no key: {config.allow_no_key}")
    
    if config.chain_override:
        print(f"  Chain override: {config.chain_override}")
    
    return config


def validate_chain_resolution(config):
    """Validate chain code resolution."""
    print("\n🔗 Validating chain code resolution...")
    
    test_chains = [1, 10, 8453, 42161, 100, 137, 56, 999999]  # Including unknown chain
    
    for chain_id in test_chains:
        chain_code = config.get_chain_code(chain_id)
        known = chain_id in config.CHAIN_CODE_MAP
        print(f"  Chain {chain_id}: {chain_code} {'✓' if known else '⚠'}")
    
    return True


def validate_client_creation():
    """Validate client creation for different chains."""
    print("\n🏗️  Validating client creation...")
    
    test_chains = [1, 10, 42161]  # Test a few major chains
    
    for chain_id in test_chains:
        try:
            client = SafeTransactionServiceClient(chain_id)
            print(f"  Chain {chain_id} ({client.chain_code}): ✓ Client created")
            print(f"    Base URL: {client.base_url}")
        except ApiError as e:
            if "API_KEY is required" in str(e):
                print(f"  Chain {chain_id}: ⚠ API key required (expected in prod)")
            else:
                print(f"  Chain {chain_id}: ✗ {e}")
                return False
        except Exception as e:
            print(f"  Chain {chain_id}: ✗ Unexpected error: {e}")
            return False
    
    return True


def validate_api_connectivity():
    """Test basic API connectivity if API key is available."""
    print("\n🌐 Validating API connectivity...")
    
    config = SafeTransactionServiceConfig()
    if not config.api_key:
        if config.allow_no_key:
            print("  ⚠ No API key set, skipping connectivity test")
            return True
        else:
            print("  ✗ No API key set and SAFE_TX_ALLOW_NO_KEY not enabled")
            return False
    
    # Test with mainnet (most stable)
    try:
        client = SafeTransactionServiceClient(1)  # mainnet
        
        # Test a lightweight endpoint - getting about info
        try:
            response = client.get('/api/v1/about/')
            if response.status_code == 200:
                about_info = response.json()
                print(f"  ✓ Successfully connected to {client.base_url}")
                print(f"    API Version: {about_info.get('version', 'unknown')}")
                return True
            else:
                print(f"  ✗ API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"  ✗ API connection failed: {e}")
            return False
            
    except ApiError as e:
        print(f"  ✗ Client creation failed: {e}")
        return False


def validate_headers():
    """Validate that proper headers are being set."""
    print("\n📋 Validating request headers...")
    
    try:
        client = SafeTransactionServiceClient(1)
        headers = client._get_headers()
        
        required_headers = ['Accept', 'User-Agent']
        for header in required_headers:
            if header in headers:
                print(f"  ✓ {header}: {headers[header]}")
            else:
                print(f"  ✗ Missing required header: {header}")
                return False
        
        if client.config.api_key:
            if 'Authorization' in headers:
                print(f"  ✓ Authorization: Bearer ***{client.config.api_key[-4:]}")
            else:
                print("  ✗ Missing Authorization header despite API key being set")
                return False
        else:
            print("  ⚠ No Authorization header (no API key)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Header validation failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("🛡️  Safe Transaction Service API Validation")
    print("=" * 50)
    
    tests = [
        ("Configuration", validate_config),
        ("Chain Resolution", lambda: validate_chain_resolution(SafeTransactionServiceConfig())),
        ("Client Creation", validate_client_creation),
        ("Headers", validate_headers),
        ("API Connectivity", validate_api_connectivity),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if test_name == "Configuration":
                test_func()  # Config validation doesn't return boolean
                results.append((test_name, True))
            else:
                success = test_func()
                results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Validation Summary:")
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All validations passed! Safe API integration is ready.")
        return 0
    else:
        print("\n⚠️  Some validations failed. Check configuration and API key.")
        return 1


if __name__ == "__main__":
    sys.exit(main())