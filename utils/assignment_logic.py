# utils/assignment_logic.py
import random
from models import User, Assignment, db

class AssignmentGenerator:
    @staticmethod
    def generate_assignments():
        """
        Generate Secret Santa assignments ensuring:
        1. No self-assignment
        2. No cycles of 2 (A->B, B->A)
        3. Each person is both a gifter and giftee exactly once
        """
        users = User.query.all()
        
        if len(users) < 3:
            raise ValueError("Need at least 3 participants for Secret Santa")
        
        # Clear existing assignments
        Assignment.query.delete()
        
        # Create a derangement (permutation where no element appears in its original position)
        assignments = AssignmentGenerator._create_derangement([u.id for u in users])
        
        # Create assignment records
        for gifter_id, giftee_id in assignments.items():
            assignment = Assignment(
                gifter_user_id=gifter_id,
                giftee_user_id=giftee_id
            )
            db.session.add(assignment)
        
        db.session.commit()
        return len(assignments)
    
    @staticmethod
    def _create_derangement(ids):
        """
        Create a derangement - a permutation where no element maps to itself
        and avoid immediate cycles (A->B, B->A)
        """
        max_attempts = 1000
        
        for _ in range(max_attempts):
            shuffled = ids.copy()
            random.shuffle(shuffled)
            
            # Check if valid derangement
            valid = True
            assignments = {}
            
            for i, original_id in enumerate(ids):
                new_id = shuffled[i]
                
                # No self-assignment
                if original_id == new_id:
                    valid = False
                    break
                
                # No immediate cycles
                if new_id in assignments and assignments[new_id] == original_id:
                    valid = False
                    break
                
                assignments[original_id] = new_id
            
            if valid:
                return assignments
        
        # Fallback: simple rotation (guaranteed to work)
        return {ids[i]: ids[(i + 1) % len(ids)] for i in range(len(ids))}
    
    @staticmethod
    def get_assignment_map():
        """Get all assignments for admin view"""
        assignments = Assignment.query.all()
        result = []
        
        for assignment in assignments:
            result.append({
                'id': assignment.id,
                'gifter': {
                    'id': assignment.gifter.id,
                    'name': assignment.gifter.name,
                    'emp_id': assignment.gifter.emp_id,
                    'email': assignment.gifter.email
                },
                'giftee': {
                    'id': assignment.giftee.id,
                    'name': assignment.giftee.name,
                    'emp_id': assignment.giftee.emp_id,
                    'email': assignment.giftee.email,
                    'preferences': assignment.giftee.preferences,
                    'address': assignment.giftee.address
                },
                'reveal_completed': assignment.reveal_completed,
                'reveal_time': assignment.reveal_time.isoformat() if assignment.reveal_time else None
            })
        
        return result
