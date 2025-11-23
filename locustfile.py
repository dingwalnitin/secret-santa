import random
import string
import time
from locust import HttpUser, TaskSet, task, between, events

# Admin credentials
ADMIN_EMAIL = "nitin@zs.com"
ADMIN_PASSWORD = "1q2w1q2w"

# Global state management
registered_users = []
registration_complete = False
assignments_generated = False
phase2_active = False

def random_string(length=8):
    """Generate random string for user data"""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_name():
    """Generate random name"""
    first_names = ["John", "Jane", "Mike", "Sarah", "David", "Emma", "Chris", "Lisa", "Tom", "Amy",
                   "Robert", "Mary", "James", "Patricia", "Michael", "Jennifer", "William", "Linda"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", 
                  "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


class UserRegistrationTasks(TaskSet):
    """User registration behavior - Phase 1"""
    
    @task
    def register_user(self):
        """Register a new user"""
        global registered_users, registration_complete

        if len(registered_users) >= 10:
            if not registration_complete:
                registration_complete = True
                print(f"\n✅ Registration complete! {len(registered_users)} users registered\n")
            self.interrupt()
            return

        name = random_name()
        emp_id = f"EMP{random.randint(10000, 99999)}"
        email = f"{random_string(6)}@company.com"
        preferences = random.choice([
            "I love books, coffee, and tech gadgets",
            "Into fitness, sports equipment, and healthy snacks",
            "Art enthusiast - paintings, sketches, crafts",
            "Gaming fan - PC games, board games, puzzles",
            "Music lover - headphones, vinyl records, instruments",
            "Cooking enthusiast - kitchen tools, cookbooks",
            "Travel lover - maps, travel accessories, guides",
            "Photography fan - camera accessories, photo albums"
        ])
        address = f"{random.randint(1, 999)} {random.choice(['Main', 'Oak', 'Maple', 'Park'])} Street, City, State {random.randint(10000, 99999)}"

        with self.client.post(
            "/register",
            data={
                "name": name,
                "emp_id": emp_id,
                "email": email,
                "preferences": preferences,
                "address": address
            },
            allow_redirects=True,
            catch_response=True
        ) as response:

            if response.status_code == 200:
                if "already registered" not in response.text.lower():

                    registered_users.append({
                        "name": name,
                        "emp_id": emp_id,
                        "email": email
                    })

                    if len(registered_users) % 10 == 0:
                        print(f"📝 Registered {len(registered_users)} users...")

                    response.success()
                else:
                    response.failure("Duplicate registration")
            else:
                response.failure(f"Registration failed with status {response.status_code}")


class AdminTasksSequential(TaskSet):
    """Admin behavior - Phase 2"""
    
    def on_start(self):
        """Login as admin first"""
        self.admin_logged_in = False
        self.login_admin()
    
    

    def login_admin(self):
        """Admin login"""
        with self.client.post(
            "/admin/login",
            data={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            },
            allow_redirects=False,
            catch_response=True
        ) as response:

            if response.status_code in [200, 302]:
                self.admin_logged_in = True
                print("🔐 Admin logged in successfully")
                response.success()
            else:
                print(f"❌ Admin login failed: {response.status_code}")
                response.failure("Admin login failed")

    
    @task(1)
    def generate_assignments_once(self):
        """Generate Secret Santa assignments - only once"""
        global assignments_generated, registered_users
        
        if not self.admin_logged_in:
            return
        
        if assignments_generated:
            return
        
        if len(registered_users) < 3:
            print(f"⏳ Waiting for more users... ({len(registered_users)}/3 minimum)")
            return
        
        response = self.client.post("/admin/assignments/generate", 
                                   allow_redirects=True, 
                                   catch_response=True)
        
        if response.status_code == 200:
            assignments_generated = True
            print(f"✅ Assignments generated for {len(registered_users)} users!")
            response.success()
        else:
            response.failure("Assignment generation failed")
    
    @task(2)
    def activate_phase_2_once(self):
        """Activate Phase 2 - only once after assignments generated"""
        global phase2_active, assignments_generated
        
        if not self.admin_logged_in:
            return
        
        if phase2_active:
            return
        
        if not assignments_generated:
            return
        
        response = self.client.post("/admin/settings", data={
            "action": "update_phase",
            "phase": "2"
        }, allow_redirects=True, catch_response=True)
        
        if response.status_code == 200:
            phase2_active = True
            print("🚀 Phase 2 activated! Users can now login and reveal!")
            response.success()
        else:
            response.failure("Phase 2 activation failed")
    
    @task(3)
    def view_dashboard(self):
        """View admin dashboard"""
        if self.admin_logged_in:
            self.client.get("/admin/dashboard")
    
    @task(1)
    def view_participants(self):
        """View participants"""
        if self.admin_logged_in:
            self.client.get("/admin/participants")
    
    @task(1)
    def view_assignments(self):
        """View assignments"""
        if self.admin_logged_in:
            self.client.get("/admin/assignments")


class UserLoginAndRevealTasks(TaskSet):
    """User login and reveal behavior - Phase 3"""
    
    def on_start(self):
        """Wait for Phase 2 and select a user"""
        global phase2_active, registered_users
        
        # Wait for Phase 2
        max_wait = 60  # Wait up to 60 seconds
        waited = 0
        while not phase2_active and waited < max_wait:
            time.sleep(1)
            waited += 1
        
        if not phase2_active:
            print("⚠️ Phase 2 not active yet, stopping user task")
            self.interrupt()
            return
        
        # Check if we have registered users
        if not registered_users:
            print("⚠️ No registered users available")
            self.interrupt()
            return
        
        # Select a random user
        self.user_data = random.choice(registered_users)
        self.logged_in = False
        self.revealed = False
        self.login()
    
    def login(self):
        with self.client.post(
            "/login",
            data={
                "email": self.user_data["email"],
                "emp_id": self.user_data["emp_id"]
            },
            allow_redirects=False,
            catch_response=True
        ) as response:
            if response.status_code in [200, 302]:
                self.logged_in = True
                print(f"✅ User logged in: {self.user_data['name']}")
                response.success()
            else:
                print(f"❌ User login failed: {response.status_code}")
                response.failure("Login failed")

    
    @task(5)
    def spin_wheel_and_reveal(self):
        """Spin the wheel and reveal assignment"""
        if not self.logged_in:
            return
        
        if self.revealed:
            # Already revealed, just view dashboard
            self.client.get("/dashboard")
            return
        
        # First, access the reveal page
        response = self.client.get("/reveal", catch_response=True)
        
        if response.status_code == 200:
            print(f"🎡 {self.user_data['name']} is spinning the wheel...")
            
            # Complete the reveal
            reveal_response = self.client.post("/api/complete-reveal",
                                              headers={"Content-Type": "application/json"},
                                              catch_response=True)
            
            if reveal_response.status_code == 200:
                self.revealed = True
                print(f"🎉 {self.user_data['name']} revealed their Secret Santa match!")
                reveal_response.success()
            else:
                reveal_response.failure("Reveal completion failed")
            
            response.success()
        else:
            response.failure("Could not access reveal page")
    
    @task(3)
    def view_dashboard(self):
        """View user dashboard"""
        if self.logged_in and self.revealed:
            self.client.get("/dashboard")
    
    @task(2)
    def view_chat(self):
        """View chat page"""
        if self.logged_in and self.revealed:
            self.client.get("/chat")


# Event hooks
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*70)
    print("🎅 SECRET SANTA LOAD TEST - SEQUENTIAL WORKFLOW 🎅")
    print("="*70)
    print(f"Admin: {ADMIN_EMAIL}")
    print("\nWorkflow:")
    print("  Phase 1: User Registration (100 users)")
    print("  Phase 2: Admin generates assignments and activates Phase 2")
    print("  Phase 3: Users login and reveal their matches")
    print("="*70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n" + "="*70)
    print("🎄 SECRET SANTA LOAD TEST COMPLETED 🎄")
    print("="*70)
    print(f"Total users registered: {len(registered_users)}")
    print(f"Assignments generated: {'✅ Yes' if assignments_generated else '❌ No'}")
    print(f"Phase 2 activated: {'✅ Yes' if phase2_active else '❌ No'}")
    print("="*70 + "\n")


# ============================================================================
# USAGE: Run in 3 separate phases (RECOMMENDED)
# ============================================================================

class Phase1_Registration(HttpUser):
    """Phase 1: Only registration"""
    wait_time = between(0.1, 0.5)
    tasks = [UserRegistrationTasks]


class Phase2_Admin(HttpUser):
    """Phase 2: Admin setup"""
    wait_time = between(2, 5)
    tasks = [AdminTasksSequential]


class Phase3_UserReveals(HttpUser):
    """Phase 3: User logins and reveals"""
    wait_time = between(1, 3)
    tasks = [UserLoginAndRevealTasks]