#!/usr/bin/env python3
"""
Test script to verify redirect URI construction for Cloud Run deployment.

This script simulates how the redirect URI will be constructed when the 
application is deployed on Google Cloud Run.
"""

from urllib.parse import urlparse, urlunparse


def construct_redirect_uri(host_url):
    """
    Construct the OAuth redirect URI from a host URL.
    This mirrors the logic in main.py qbo_oauth_authorize_v2().
    """
    parsed_url = urlparse(host_url.rstrip('/'))
    https_url = urlunparse((
        'https',  # scheme
        parsed_url.netloc,  # netloc
        parsed_url.path,  # path
        parsed_url.params,  # params
        parsed_url.query,  # query
        parsed_url.fragment  # fragment
    ))
    redirect_uri = https_url + '/api/qbo/oauth/callback'
    return redirect_uri


def test_cloud_run_url():
    """Test with the actual Cloud Run URL."""
    # Test cases
    test_cases = [
        {
            'name': 'Cloud Run HTTPS',
            'input': 'https://feb42026-286597576168.us-central1.run.app/',
            'expected': 'https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback'
        },
        {
            'name': 'Cloud Run HTTP (should convert to HTTPS)',
            'input': 'http://feb42026-286597576168.us-central1.run.app/',
            'expected': 'https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback'
        },
        {
            'name': 'Cloud Run without trailing slash',
            'input': 'https://feb42026-286597576168.us-central1.run.app',
            'expected': 'https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback'
        },
        {
            'name': 'Localhost HTTPS',
            'input': 'https://localhost:8080/',
            'expected': 'https://localhost:8080/api/qbo/oauth/callback'
        },
        {
            'name': 'Localhost HTTP (should convert to HTTPS)',
            'input': 'http://localhost:8080/',
            'expected': 'https://localhost:8080/api/qbo/oauth/callback'
        }
    ]
    
    print("=" * 80)
    print("OAuth Redirect URI Construction Test")
    print("=" * 80)
    print()
    
    all_passed = True
    for test_case in test_cases:
        result = construct_redirect_uri(test_case['input'])
        passed = result == test_case['expected']
        all_passed = all_passed and passed
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_case['name']}")
        print(f"  Input:    {test_case['input']}")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Got:      {result}")
        print()
    
    print("=" * 80)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 80)
    print()
    
    # Show the expected redirect URI for QuickBooks Developer Portal
    print("IMPORTANT: Register this redirect URI in QuickBooks Developer Portal:")
    print("https://feb42026-286597576168.us-central1.run.app/api/qbo/oauth/callback")
    print()
    
    return all_passed


if __name__ == '__main__':
    import sys
    success = test_cloud_run_url()
    sys.exit(0 if success else 1)
