# Eyes Outside Aviation Flight School Management System

A Flask-based web application for managing a small flight school's operations, including student registration, aircraft and instructor booking, and administrative functions.

## Features

- Student registration and authentication
- Aircraft and instructor booking system
- Administrative dashboard for managing resources
- Calendar view for scheduling
- Email notifications (placeholder for future implementation)

## Project Structure

```
flightschool/
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── templates/
│   └── static/
├── tests/
├── config.py
├── requirements.txt
└── run.py
```

## Setup Instructions

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file with the following variables:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   DATABASE_URL=sqlite:///flightschool.db
   ```

4. Initialize the database:
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

5. Run the application:
   ```bash
   flask run
   ```

## Testing

Run the test suite:
```bash
pytest
```

## Development Guidelines

- All new features must include corresponding tests
- Follow PEP 8 style guide
- Write clear, maintainable code with appropriate documentation
- Ensure all tests pass before committing changes 