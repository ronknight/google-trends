import unittest
import json
from app import app # Assuming your Flask app object is named 'app' in app.py

class TestApiCompare(unittest.TestCase):

    def setUp(self):
        """Set up test client and other test variables."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_api_compare_success(self):
        """Test successful API call to /api/compare."""
        payload = {
            "keywords": ["python", "javascript"],
            "timeframe": "today 1-m"
        }
        response = self.client.post('/api/compare', json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        
        data = json.loads(response.data)
        self.assertIsInstance(data, dict)
        self.assertIn('schema', data)
        self.assertIn('data', data)
        self.assertIsInstance(data['schema'].get('fields'), list)
        self.assertIsInstance(data['data'], list)
        # Due to external API call, we might get no data if Google blocks
        # So, we can't always assert that data['data'] is non-empty without mocking
        # For now, checking structure is sufficient for this basic test

    def test_api_compare_missing_keywords(self):
        """Test API call with missing 'keywords' field."""
        payload = {
            "timeframe": "today 1-m"
        }
        response = self.client.post('/api/compare', json=payload)
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], "Please provide at least two keywords as a list.")

    def test_api_compare_insufficient_keywords(self):
        """Test API call with only one keyword."""
        payload = {
            "keywords": ["python"],
            "timeframe": "today 1-m"
        }
        response = self.client.post('/api/compare', json=payload)
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], "Please provide at least two keywords as a list.")

    def test_api_compare_too_many_keywords(self):
        """Test API call with more than five keywords."""
        payload = {
            "keywords": ["k1", "k2", "k3", "k4", "k6", "k7"],
            "timeframe": "today 1-m"
        }
        response = self.client.post('/api/compare', json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], "Cannot compare more than five keywords.")

    def test_api_compare_invalid_payload(self):
        """Test API call with invalid (non-JSON) payload."""
        response = self.client.post('/api/compare', data="this is not json")
        
        self.assertEqual(response.status_code, 400) # Werkzeug/Flask handles non-JSON as bad request
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data)
        self.assertIn('error', data)
        # The exact message can vary depending on Flask version, 
        # but it should indicate a JSON parsing error.
        self.assertTrue("Invalid JSON payload" in data['error'] or "Failed to decode JSON" in data['error'])


if __name__ == '__main__':
    unittest.main()
