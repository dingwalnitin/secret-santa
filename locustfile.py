"""
Load Testing Script for Secret Santa Application
Uses Locust to simulate multiple users accessing the application simultaneously

Install: pip install locust
Run: locust -f locustfile.py --host=https://your-app.azurewebsites.net
Then open http://localhost:8089 in browser to configure and start test
"""

from locust import HttpUser, task, between, events
import random
import logging

# Sample user data for testing
SAMPLE_USERS = [
    {"email": f"user{i}@example.com", "emp_id": f"EMP{i:03d}"} 
    for i in range(1, 51)  # 50 test users
]


class SecretSantaUser(HttpUser):
    """
    Simulates a Secret Santa application user
    """
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """
        Called when a user starts - simulates login
        """
        # Pick a random user to simulate
        self.user_data = random.choice(SAMPLE_USERS)
        
        # Try to login
        response = self.client.post("/login", {
            "email": self.user_data["email"],
            "emp_id": self.user_data["emp_id"]
        }, catch_response=True)
        
        if response.status_code == 200:
            # Check if we got redirected to dashboard (successful login)
            if "/dashboard" in response.url or "dashboard" in response.text.lower():
                self.logged_in = True
                logging.info(f"User {self.user_data['email']} logged in successfully")
            else:
                self.logged_in = False
                logging.warning(f"User {self.user_data['email']} login failed - may not exist in DB")
        else:
            self.logged_in = False
            logging.error(f"Login failed for {self.user_data['email']}: {response.status_code}")
    
    @task(5)
    def view_homepage(self):
        """
        Visit the homepage
        Weight: 5 (most common action)
        """
        self.client.get("/", name="Homepage")
    
    @task(3)
    def view_dashboard(self):
        """
        View user dashboard (requires login)
        Weight: 3
        """
        if not hasattr(self, 'logged_in') or not self.logged_in:
            # Skip if not logged in
            return
            
        response = self.client.get("/dashboard", name="Dashboard", catch_response=True)
        
        if response.status_code == 200:
            response.success()
        elif response.status_code == 302:
            # Redirect to login - session expired
            logging.info("Session expired, re-login needed")
            response.failure("Session expired")
        else:
            response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def view_reveal(self):
        """
        View the reveal page with spin wheel
        Weight: 2 (less common but important to test)
        """
        if not hasattr(self, 'logged_in') or not self.logged_in:
            return
            
        response = self.client.get("/reveal", name="Reveal Page", catch_response=True)
        
        if response.status_code == 200:
            # Check if spin wheel assets are loaded
            if "spin-wheel.js" in response.text:
                response.success()
            else:
                response.failure("Spin wheel JS not found in page")
        elif response.status_code == 302:
            # Might redirect if already revealed
            response.success()
        else:
            response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def complete_reveal(self):
        """
        Complete the reveal (mark as revealed)
        Weight: 1 (happens once per user)
        """
        if not hasattr(self, 'logged_in') or not self.logged_in:
            return
            
        response = self.client.post("/api/complete-reveal", 
                                   name="Complete Reveal API",
                                   catch_response=True)
        
        # It's ok if this fails (user already revealed)
        if response.status_code in [200, 400]:
            response.success()
        else:
            response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def view_chat(self):
        """
        View chat page
        Weight: 2
        """
        if not hasattr(self, 'logged_in') or not self.logged_in:
            return
            
        self.client.get("/chat", name="Chat Page", catch_response=True)
    
    @task(1)
    def load_static_assets(self):
        """
        Load static assets (CSS, JS, images)
        Weight: 1
        """
        assets = [
            "/static/css/style.css",
            "/static/js/main.js",
            "/static/js/spin-wheel.js",
            "/static/js/chat.js",
        ]
        
        asset = random.choice(assets)
        self.client.get(asset, name="Static Assets")


class AdminUser(HttpUser):
    """
    Simulates an admin user accessing the admin panel
    """
    wait_time = between(3, 10)  # Admins check less frequently
    weight = 1  # Only 1 admin for every 10 regular users
    
    def on_start(self):
        """Admin login"""
        # Try to login as admin
        response = self.client.post("/admin/login", {
            "email": "admin@example.com",
            "password": "admin123"  # Change to match your test admin
        }, catch_response=True)
        
        if response.status_code == 200 and "/admin/dashboard" in response.url:
            self.logged_in = True
            logging.info("Admin logged in successfully")
        else:
            self.logged_in = False
            logging.warning("Admin login failed")
    
    @task(5)
    def view_admin_dashboard(self):
        """View admin dashboard"""
        if not hasattr(self, 'logged_in') or not self.logged_in:
            return
            
        self.client.get("/admin/dashboard", name="Admin Dashboard")
    
    @task(3)
    def view_participants(self):
        """View participants list"""
        if not hasattr(self, 'logged_in') or not self.logged_in:
            return
            
        self.client.get("/admin/participants", name="Admin Participants")
    
    @task(2)
    def view_assignments(self):
        """View assignments"""
        if not hasattr(self, 'logged_in') or not self.logged_in:
            return
            
        self.client.get("/admin/assignments", name="Admin Assignments")
    
    @task(1)
    def view_settings(self):
        """View settings"""
        if not hasattr(self, 'logged_in') or not self.logged_in:
            return
            
        self.client.get("/admin/settings", name="Admin Settings")


# Event listeners for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    logging.info("=" * 80)
    logging.info("Secret Santa Load Test Starting")
    logging.info("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    logging.info("=" * 80)
    logging.info("Secret Santa Load Test Completed")
    logging.info("=" * 80)


# Custom user class for registration testing (separate test)
class RegistrationUser(HttpUser):
    """
    Simulates new users registering
    Only use this for registration phase testing
    """
    wait_time = between(2, 8)
    
    @task
    def register_new_user(self):
        """Register a new user"""
        user_num = random.randint(1000, 9999)
        response = self.client.post("/register", {
            "name": f"Test User {user_num}",
            "emp_id": f"TEST{user_num}",
            "email": f"test{user_num}@example.com",
            "address": f"{user_num} Test Street",
            "preferences": "Books, Coffee, Tech gadgets"
        }, name="Registration", catch_response=True)
        
        if response.status_code == 200:
            if "successfully" in response.text.lower() or "success" in response.text.lower():
                response.success()
            else:
                response.failure("Registration may have failed")
        else:
            response.failure(f"Registration failed: {response.status_code}")


"""
USAGE EXAMPLES:

1. Basic load test with web UI:
   locust -f locustfile.py --host=https://your-app.azurewebsites.net
   Then open http://localhost:8089 and configure:
   - Number of users: 100
   - Spawn rate: 10 users/second
   
2. Headless mode (no web UI):
   locust -f locustfile.py --host=https://your-app.azurewebsites.net \
          --users 100 --spawn-rate 10 --run-time 5m --headless
   
3. Test specific user class only:
   locust -f locustfile.py --host=https://your-app.azurewebsites.net \
          SecretSantaUser --users 50 --spawn-rate 5

4. Test registration (Phase 1):
   locust -f locustfile.py --host=https://your-app.azurewebsites.net \
          RegistrationUser --users 20 --spawn-rate 2

5. Generate HTML report:
   locust -f locustfile.py --host=https://your-app.azurewebsites.net \
          --users 100 --spawn-rate 10 --run-time 10m --headless \
          --html report.html --csv results

RECOMMENDED TEST SCENARIOS:

Scenario 1: Normal Load
- Users: 50
- Spawn rate: 5/sec
- Duration: 10 minutes
- Expected: 0% errors, avg response < 1s

Scenario 2: Peak Load (reveal time)
- Users: 200
- Spawn rate: 20/sec
- Duration: 5 minutes
- Expected: < 1% errors, avg response < 2s

Scenario 3: Stress Test
- Users: 500
- Spawn rate: 50/sec
- Duration: 3 minutes
- Expected: < 5% errors, understand breaking point

METRICS TO MONITOR DURING TESTING:

1. Application Metrics (via Locust):
   - Requests per second (RPS)
   - Average response time
   - 95th percentile response time
   - Error rate
   - Concurrent users

2. Server Metrics (via Azure Portal):
   - CPU percentage (target: < 70%)
   - Memory percentage (target: < 80%)
   - HTTP server errors (target: < 1%)
   - Average response time (target: < 2s)
   - Data In/Out

3. Database Metrics (via Azure Portal):
   - DTU percentage (target: < 80%)
   - Active connections (target: < 80% of limit)
   - Slow query count
   - Deadlocks (target: 0)

4. Redis Metrics (if using):
   - Server load (target: < 70%)
   - Connected clients
   - Used memory (target: < 80%)

SUCCESS CRITERIA:

✅ Pass:
- Error rate < 1%
- Average response time < 2s
- 95th percentile < 5s
- No server crashes
- All static assets load

❌ Fail:
- Error rate > 5%
- Frequent 500 errors
- Response time > 5s consistently
- Server crashes or restarts
- Static assets fail to load

TROUBLESHOOTING:

High error rates:
- Check application logs
- Verify database connections not exhausted
- Check if workers are crashing
- Verify Redis connection

Slow response times:
- Check database query performance
- Verify static files being served efficiently
- Check if workers are sufficient
- Look for blocking operations

Connection errors:
- Verify WebSocket support enabled
- Check CORS configuration
- Verify SSL/TLS setup
- Check firewall rules
"""
