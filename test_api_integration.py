#!/usr/bin/env python3
"""
Integration tests for library API endpoints
"""
import os
import sys
import json
import time
import signal
import subprocess
import requests
from multiprocessing import Process

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def start_test_server():
    """Start Flask server in test mode"""
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    os.environ['SPOTIFY_CLIENT_ID'] = 'test_client_id'
    os.environ['SPOTIFY_CLIENT_SECRET'] = 'test_client_secret'
    os.environ['FLASK_ENV'] = 'testing'
    
    # Import and run server
    import server
    server.app.run(host='127.0.0.1', port=5555, debug=False)


def test_library_endpoints():
    """Test library API endpoints"""
    base_url = 'http://127.0.0.1:5555'
    
    print("\nTest: Library API Endpoints")
    print("-" * 60)
    
    # Wait for server to start
    time.sleep(2)
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get(f'{base_url}/library/songs', timeout=2)
            break
        except requests.exceptions.ConnectionError:
            if i == max_retries - 1:
                print("✗ Server failed to start")
                return False
            time.sleep(1)
    
    try:
        # Test 1: Get empty library
        response = requests.get(f'{base_url}/library/songs')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data['success'] == True
        print(f"✓ GET /library/songs: {data['count']} songs")
        
        # Test 2: Add song to library
        song_data = {
            'title': 'Integration Test Song',
            'artist': 'Test Artist',
            'audio_features': {'tempo': 120, 'energy': 0.8},
            'spotify_id': 'test_integration_id'
        }
        response = requests.post(f'{base_url}/library/songs', json=song_data)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        data = response.json()
        assert data['success'] == True
        song_id = data['song_id']
        print(f"✓ POST /library/songs: Song added with ID {song_id}")
        
        # Test 3: Get library with song
        response = requests.get(f'{base_url}/library/songs')
        data = response.json()
        assert data['count'] >= 1
        print(f"✓ GET /library/songs: Now has {data['count']} songs")
        
        # Test 4: Create collection
        collection_data = {
            'name': 'Integration Test Collection',
            'description': 'Test collection for API testing'
        }
        response = requests.post(f'{base_url}/library/collections', json=collection_data)
        assert response.status_code == 201
        data = response.json()
        assert data['success'] == True
        collection_id = data['collection_id']
        print(f"✓ POST /library/collections: Collection created with ID {collection_id}")
        
        # Test 5: Get collections
        response = requests.get(f'{base_url}/library/collections')
        data = response.json()
        assert data['success'] == True
        assert data['count'] >= 1
        print(f"✓ GET /library/collections: {data['count']} collections")
        
        # Test 6: Add song to collection
        response = requests.post(
            f'{base_url}/library/collections/{collection_id}/songs',
            json={'song_id': song_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        print(f"✓ POST /library/collections/{collection_id}/songs: Song added")
        
        # Test 7: Get collection with songs
        response = requests.get(f'{base_url}/library/collections/{collection_id}')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert len(data['collection']['songs']) == 1
        print(f"✓ GET /library/collections/{collection_id}: Collection has 1 song")
        
        # Test 8: Get library stats
        response = requests.get(f'{base_url}/library/stats')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        stats = data['stats']
        print(f"✓ GET /library/stats: {stats['total_songs']} songs, {stats['total_collections']} collections")
        
        # Test 9: Remove song from collection
        response = requests.delete(f'{base_url}/library/collections/{collection_id}/songs/{song_id}')
        assert response.status_code == 200
        print(f"✓ DELETE /library/collections/{collection_id}/songs/{song_id}: Song removed")
        
        # Test 10: Delete collection
        response = requests.delete(f'{base_url}/library/collections/{collection_id}')
        assert response.status_code == 200
        print(f"✓ DELETE /library/collections/{collection_id}: Collection deleted")
        
        # Test 11: Delete song
        response = requests.delete(f'{base_url}/library/songs/{song_id}')
        assert response.status_code == 200
        print(f"✓ DELETE /library/songs/{song_id}: Song deleted")
        
        print("\n✓ All API endpoint tests passed!")
        return True
        
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run integration tests"""
    print("=" * 60)
    print("Library API Integration Tests")
    print("=" * 60)
    
    # Start server in subprocess
    print("\nStarting test server on port 5555...")
    server_process = Process(target=start_test_server)
    server_process.start()
    
    try:
        # Run tests
        success = test_library_endpoints()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ All integration tests passed!")
            return 0
        else:
            print("✗ Some integration tests failed")
            return 1
    finally:
        # Stop server
        print("\nStopping test server...")
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            server_process.kill()


if __name__ == '__main__':
    sys.exit(main())
