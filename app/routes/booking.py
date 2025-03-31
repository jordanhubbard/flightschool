from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, abort
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice
from app import db
from app.forms import BookingForm, CheckInForm, CheckOutForm, InvoiceForm
from datetime import datetime, timedelta
from app.calendar_service import GoogleCalendarService

bp = Blueprint('booking', __name__)
calendar_service = GoogleCalendarService()

@bp.route('/google-auth')
@login_required
def google_auth():
    """Start Google Calendar OAuth2 flow."""
    authorization_url = calendar_service.get_authorization_url()
    return redirect(authorization_url)

@bp.route('/google-callback')
@login_required
def google_callback():
    """Handle Google Calendar OAuth2 callback."""
    code = request.args.get('code')
    if not code:
        flash('Failed to authenticate with Google Calendar')
        return redirect(url_for('booking.dashboard'))
    
    try:
        credentials = calendar_service.handle_callback(code)
        session['google_credentials'] = credentials.to_json()
        flash('Successfully connected to Google Calendar')
    except Exception as e:
        flash(f'Error connecting to Google Calendar: {str(e)}')
    
    return redirect(url_for('booking.dashboard'))

@bp.route('/dashboard')
@login_required
def dashboard():
    aircraft = Aircraft.query.filter_by(status='available').all()
    instructors = User.query.filter(User.certificates.isnot(None)).all()  # Get users with certificates (instructors)
    user_bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time).all()
    has_google_auth = current_user.google_calendar_enabled
    return render_template('booking/dashboard.html',
                         aircraft=aircraft,
                         instructors=instructors,
                         bookings=user_bookings,
                         has_google_auth=has_google_auth)

@bp.route('/book', methods=['POST'])
@login_required
def create_booking():
    try:
        if request.form.get('start_time'):
            start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        else:
            start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%d %H:%M')
        
        duration = int(request.form.get('duration', 1))
        aircraft_id = request.form.get('aircraft_id')
        instructor_id = request.form.get('instructor_id')
        
        end_time = start_time + timedelta(hours=duration)
        
        # Check for conflicts
        existing_booking = Booking.query.filter(
            Booking.aircraft_id == aircraft_id,
            Booking.status == 'scheduled',
            Booking.start_time <= end_time,
            Booking.end_time >= start_time
        ).first()
        
        if existing_booking:
            flash('Aircraft is already booked')
            return redirect(url_for('booking.dashboard'))
        
        if instructor_id:
            instructor_booking = Booking.query.filter(
                Booking.instructor_id == instructor_id,
                Booking.status == 'scheduled',
                Booking.start_time <= end_time,
                Booking.end_time >= start_time
            ).first()
            
            if instructor_booking:
                flash('Instructor is already booked')
                return redirect(url_for('booking.dashboard'))
        
        booking = Booking(
            student_id=current_user.id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            start_time=start_time,
            end_time=end_time,
            status='scheduled'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        # Create Google Calendar events for all relevant users
        if instructor_id:
            instructor = User.query.get(instructor_id)
            if instructor and instructor.google_calendar_enabled:
                try:
                    event_id = calendar_service.create_event(booking, instructor)
                    if event_id:
                        booking.google_calendar_event_id = event_id
                        db.session.commit()
                except Exception as e:
                    flash(f'Booking created but failed to add to instructor\'s Google Calendar: {str(e)}')
        
        # Add to student's calendar
        if current_user.google_calendar_enabled:
            try:
                event_id = calendar_service.create_event(booking, current_user)
                if event_id:
                    booking.google_calendar_event_id = event_id
                    db.session.commit()
            except Exception as e:
                flash(f'Booking created but failed to add to your Google Calendar: {str(e)}')
        
        # Add to admin's calendar if exists
        admin = User.query.filter_by(is_admin=True).first()
        if admin and admin.google_calendar_enabled:
            try:
                event_id = calendar_service.create_event(booking, admin)
                if event_id:
                    booking.google_calendar_event_id = event_id
                    db.session.commit()
            except Exception as e:
                flash(f'Booking created but failed to add to admin\'s Google Calendar: {str(e)}')
        
        flash('Booking created successfully')
        return redirect(url_for('booking.dashboard'))
        
    except Exception as e:
        flash('Error creating booking. Please try again.')
        return redirect(url_for('booking.dashboard'))

@bp.route('/booking/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_booking(id):
    booking = Booking.query.get_or_404(id)
    if booking.student_id != current_user.id:
        flash('You are not authorized to cancel this booking')
        return redirect(url_for('booking.dashboard'))
    
    # Delete Google Calendar events for all relevant users
    if booking.instructor and booking.instructor.google_calendar_enabled:
        try:
            calendar_service.delete_event(booking.google_calendar_event_id, booking.instructor)
        except Exception as e:
            flash(f'Failed to delete instructor\'s Google Calendar event: {str(e)}')
    
    if current_user.google_calendar_enabled:
        try:
            calendar_service.delete_event(booking.google_calendar_event_id, current_user)
        except Exception as e:
            flash(f'Failed to delete your Google Calendar event: {str(e)}')
    
    admin = User.query.filter_by(is_admin=True).first()
    if admin and admin.google_calendar_enabled:
        try:
            calendar_service.delete_event(booking.google_calendar_event_id, admin)
        except Exception as e:
            flash(f'Failed to delete admin\'s Google Calendar event: {str(e)}')
    
    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled successfully')
    return redirect(url_for('booking.dashboard'))

@bp.route('/calendar')
@login_required
def calendar_view():
    print("\n=== Calendar View Debug ===")
    print(f"User: {current_user.email} (Admin: {current_user.is_admin}, Instructor: {current_user.is_instructor})")
    
    # Get bookings based on user role
    if current_user.is_admin:
        bookings = Booking.query.all()
        print("Fetching all bookings (admin view)")
    elif current_user.is_instructor:
        bookings = Booking.query.filter(
            (Booking.instructor_id == current_user.id) |
            (Booking.instructor_id.is_(None))
        ).all()
        print(f"Fetching instructor bookings for ID: {current_user.id}")
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).all()
        print(f"Fetching student bookings for ID: {current_user.id}")
    
    print(f"Found {len(bookings)} bookings")
    
    # Format bookings for FullCalendar
    events = []
    for booking in bookings:
        try:
            # Get student name safely
            student_name = f"{booking.student.first_name} {booking.student.last_name}" if booking.student else "Unknown Student"
            
            # Get aircraft tail number safely
            aircraft_tail = booking.aircraft.tail_number if booking.aircraft else "No Aircraft"
            
            # Get instructor name safely
            if booking.instructor:
                instructor_name = f"{booking.instructor.first_name} {booking.instructor.last_name}"
            else:
                instructor_name = 'Solo'
            
            # Set colors based on status
            status_colors = {
                'scheduled': '#28a745',  # green
                'pending': '#ffc107',    # yellow
                'completed': '#6c757d',  # gray
                'cancelled': '#dc3545'   # red
            }
            color = status_colors.get(booking.status, '#6c757d')
            
            event = {
                'id': booking.id,
                'title': f"{aircraft_tail} - {student_name}",
                'start': booking.start_time.isoformat(),
                'end': booking.end_time.isoformat(),
                'backgroundColor': color,
                'borderColor': color,
                'extendedProps': {
                    'instructor': instructor_name,
                    'status': booking.status
                }
            }
            events.append(event)
            print(f"Added event: {event}")
        except Exception as e:
            print(f"Error processing booking {booking.id}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            continue
    
    print(f"Total events: {len(events)}")
    print("=== End Calendar View Debug ===\n")
    
    has_google_auth = current_user.google_calendar_enabled
    return render_template('booking/calendar.html', events=events, has_google_auth=has_google_auth)

@bp.route('/check-in/<int:id>', methods=['GET', 'POST'])
@login_required
def check_in(id):
    booking = Booking.query.get_or_404(id)
    if booking.student_id != current_user.id:
        abort(403)
    
    if booking.status != 'confirmed':
        flash('Booking must be confirmed before check-in', 'error')
        return redirect(url_for('booking.dashboard'))
    
    if request.method == 'POST':
        try:
            hobbs_start = float(request.form['hobbs_start'])
            tach_start = float(request.form['tach_start'])
            instructor_start_time_str = request.form['instructor_start_time']
            try:
                instructor_start_time = datetime.strptime(instructor_start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                instructor_start_time = datetime.strptime(instructor_start_time_str, '%Y-%m-%d %H:%M:%S')
            notes = request.form.get('notes', '')
            
            if hobbs_start < 0:
                flash('Invalid Hobbs meter reading')
                return redirect(url_for('booking.check_in', id=id))
            
            check_in = CheckIn(
                booking_id=id,
                aircraft_id=booking.aircraft_id,
                instructor_id=booking.instructor_id,
                hobbs_start=hobbs_start,
                tach_start=tach_start,
                instructor_start_time=instructor_start_time,
                notes=notes
            )
            db.session.add(check_in)
            booking.status = 'in_progress'
            db.session.commit()
            
            flash('Check-in completed successfully', 'success')
            return redirect(url_for('booking.dashboard'))
            
        except ValueError:
            flash('Invalid input values', 'error')
            return redirect(url_for('booking.check_in', id=id))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during check-in', 'error')
            return redirect(url_for('booking.check_in', id=id))
    
    return render_template('booking/check_in.html', booking=booking)

@bp.route('/check-out/<int:id>', methods=['GET', 'POST'])
@login_required
def check_out(id):
    booking = Booking.query.get_or_404(id)
    if booking.student_id != current_user.id:
        abort(403)
    
    if booking.status != 'in_progress':
        flash('Booking must be in progress before check-out', 'error')
        return redirect(url_for('booking.dashboard'))
    
    check_in = CheckIn.query.filter_by(booking_id=id).first()
    if not check_in:
        flash('Cannot check out without checking in first', 'error')
        return redirect(url_for('booking.dashboard'))
    
    if request.method == 'POST':
        try:
            hobbs_end = float(request.form['hobbs_end'])
            tach_end = float(request.form['tach_end'])
            instructor_end_time_str = request.form['instructor_end_time']
            try:
                instructor_end_time = datetime.strptime(instructor_end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                instructor_end_time = datetime.strptime(instructor_end_time_str, '%Y-%m-%d %H:%M:%S')
            notes = request.form.get('notes', '')
            
            if hobbs_end < check_in.hobbs_start:
                flash('Hobbs end reading must be greater than start reading')
                return redirect(url_for('booking.check_out', id=id))
            
            if tach_end < check_in.tach_start:
                flash('Tach end reading must be greater than start reading')
                return redirect(url_for('booking.check_out', id=id))
            
            total_aircraft_time = hobbs_end - check_in.hobbs_start
            total_instructor_time = (instructor_end_time - check_in.instructor_start_time).total_seconds() / 3600
            
            check_out = CheckOut(
                booking_id=id,
                aircraft_id=booking.aircraft_id,
                instructor_id=booking.instructor_id,
                hobbs_end=hobbs_end,
                tach_end=tach_end,
                instructor_end_time=instructor_end_time,
                total_aircraft_time=total_aircraft_time,
                total_instructor_time=total_instructor_time,
                notes=notes
            )
            db.session.add(check_out)
            booking.status = 'completed'
            db.session.commit()
            
            flash('Check-out completed successfully', 'success')
            return redirect(url_for('booking.dashboard'))
            
        except ValueError:
            flash('Invalid input values', 'error')
            return redirect(url_for('booking.check_out', id=id))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during check-out', 'error')
            return redirect(url_for('booking.check_out', id=id))
    
    return render_template('booking/check_out.html', booking=booking, check_in=check_in)

@bp.route('/generate-invoice/<int:id>', methods=['POST'])
@login_required
def generate_invoice(id):
    booking = Booking.query.get_or_404(id)
    if booking.student_id != current_user.id:
        abort(403)
    
    check_out = CheckOut.query.filter_by(booking_id=id).first()
    if not check_out:
        return jsonify({'error': 'Cannot generate invoice without completing check-out'}), 400
    
    try:
        aircraft_total = check_out.total_aircraft_time * booking.aircraft.rate_per_hour
        instructor_total = check_out.total_instructor_time * booking.instructor.instructor_rate_per_hour if booking.instructor else 0
        total_amount = aircraft_total + instructor_total
        
        # Generate a unique invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{id}"
        
        invoice = Invoice(
            booking_id=id,
            aircraft_id=booking.aircraft_id,
            student_id=booking.student_id,
            instructor_id=booking.instructor_id,
            invoice_number=invoice_number,
            aircraft_rate=booking.aircraft.rate_per_hour,
            instructor_rate=booking.instructor.instructor_rate_per_hour if booking.instructor else None,
            aircraft_time=check_out.total_aircraft_time,
            instructor_time=check_out.total_instructor_time,
            aircraft_total=aircraft_total,
            instructor_total=instructor_total,
            total_amount=total_amount,
            status='pending'
        )
        db.session.add(invoice)
        db.session.commit()
        return jsonify({
            'message': 'Invoice generated successfully',
            'invoice': {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'aircraft_total': invoice.aircraft_total,
                'instructor_total': invoice.instructor_total,
                'total_amount': invoice.total_amount
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while generating the invoice'}), 500 