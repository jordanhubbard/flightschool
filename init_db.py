from app import create_app, db

def init_db():
    """Initialize the database."""
    app = create_app('development')
    with app.app_context():
        db.create_all()
        db.session.commit()

if __name__ == '__main__':
    init_db() 