#!/usr/bin/env python3
import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db

def init_db():
    app = create_app()
    
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Commit the changes
        db.session.commit()
        
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db() 