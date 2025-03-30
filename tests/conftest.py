import pytest
from app import create_app, db
from app.models import User, Aircraft, Booking

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        is_admin=False
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def test_admin(app):
    admin = User(
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def test_aircraft(app):
    aircraft = Aircraft(
        tail_number='N12345',
        make_model='Cessna 172',
        year=2020,
        status='available'
    )
    db.session.add(aircraft)
    db.session.commit()
    return aircraft

@pytest.fixture
def test_instructor(app):
    instructor = User(
        email='instructor@example.com',
        first_name='John',
        last_name='Doe',
        phone='123-456-7890',
        certificates='CFI, CFII',
        is_admin=False,
        is_instructor=True,
        status='active'
    )
    instructor.set_password('instructor123')
    db.session.add(instructor)
    db.session.commit()
    return instructor

@pytest.fixture
def with_csrf_token(client):
    with client.session_transaction() as session:
        session['csrf_token'] = 'test_token'
    return client 