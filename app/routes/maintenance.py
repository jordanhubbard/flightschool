from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Aircraft, MaintenanceType, MaintenanceRecord, Squawk, User
from app.forms import MaintenanceTypeForm, MaintenanceRecordForm, SquawkForm
from datetime import datetime

bp = Blueprint('maintenance', __name__)

@bp.route('/maintenance/types')
@login_required
def maintenance_types():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    types = MaintenanceType.query.all()
    return render_template('maintenance/types.html', types=types)

@bp.route('/maintenance/types/add', methods=['GET', 'POST'])
@login_required
def add_maintenance_type():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    form = MaintenanceTypeForm()
    if form.validate_on_submit():
        maintenance_type = MaintenanceType(
            name=form.name.data,
            description=form.description.data,
            interval_days=form.interval_days.data,
            interval_hours=form.interval_hours.data,
            created_by_id=current_user.id
        )
        db.session.add(maintenance_type)
        db.session.commit()
        flash('Maintenance type added successfully.', 'success')
        return redirect(url_for('maintenance.maintenance_types'))
    return render_template('maintenance/type_form.html', form=form, title='Add Maintenance Type')

@bp.route('/maintenance/types/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_maintenance_type(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    maintenance_type = MaintenanceType.query.get_or_404(id)
    form = MaintenanceTypeForm(obj=maintenance_type)
    if form.validate_on_submit():
        maintenance_type.name = form.name.data
        maintenance_type.description = form.description.data
        maintenance_type.interval_days = form.interval_days.data
        maintenance_type.interval_hours = form.interval_hours.data
        db.session.commit()
        flash('Maintenance type updated successfully.', 'success')
        return redirect(url_for('maintenance.maintenance_types'))
    return render_template('maintenance/type_form.html', form=form, title='Edit Maintenance Type')

@bp.route('/aircraft/<int:aircraft_id>/maintenance')
@login_required
def aircraft_maintenance(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    records = MaintenanceRecord.query.filter_by(aircraft_id=aircraft_id).order_by(MaintenanceRecord.performed_at.desc()).all()
    return render_template('maintenance/aircraft_maintenance.html', aircraft=aircraft, records=records)

@bp.route('/aircraft/<int:aircraft_id>/maintenance/add', methods=['GET', 'POST'])
@login_required
def add_maintenance_record(aircraft_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    form = MaintenanceRecordForm()
    form.maintenance_type.choices = [(t.id, t.name) for t in MaintenanceType.query.all()]
    form.performed_by.choices = [(u.id, u.full_name) for u in User.query.filter_by(is_admin=True).all()]
    if form.validate_on_submit():
        record = MaintenanceRecord(
            aircraft_id=aircraft_id,
            maintenance_type_id=form.maintenance_type.data,
            performed_at=form.performed_at.data,
            performed_by_id=form.performed_by.data,
            hobbs_hours=form.hobbs_hours.data,
            tach_hours=form.tach_hours.data,
            notes=form.notes.data
        )
        db.session.add(record)
        db.session.commit()
        flash('Maintenance record added successfully.', 'success')
        return redirect(url_for('maintenance.aircraft_maintenance', aircraft_id=aircraft_id))
    return render_template('maintenance/record_form.html', form=form, aircraft=aircraft, title='Add Maintenance Record')

@bp.route('/aircraft/<int:aircraft_id>/squawks')
@login_required
def aircraft_squawks(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    squawks = Squawk.query.filter_by(aircraft_id=aircraft_id).order_by(Squawk.created_at.desc()).all()
    return render_template('maintenance/aircraft_squawks.html', aircraft=aircraft, squawks=squawks)

@bp.route('/aircraft/<int:aircraft_id>/squawks/add', methods=['GET', 'POST'])
@login_required
def add_squawk(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    form = SquawkForm()
    if form.validate_on_submit():
        squawk = Squawk(
            aircraft_id=aircraft_id,
            description=form.description.data,
            status=form.status.data,
            resolution_notes=form.resolution_notes.data,
            reported_by_id=current_user.id
        )
        if form.status.data == 'resolved':
            squawk.resolved_at = datetime.utcnow()
            squawk.resolved_by_id = current_user.id
        db.session.add(squawk)
        db.session.commit()
        flash('Squawk added successfully.', 'success')
        return redirect(url_for('maintenance.aircraft_squawks', aircraft_id=aircraft_id))
    return render_template('maintenance/squawk_form.html', form=form, aircraft=aircraft, title='Add Squawk')

@bp.route('/squawks/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_squawk(id):
    squawk = Squawk.query.get_or_404(id)
    form = SquawkForm(obj=squawk)
    if form.validate_on_submit():
        squawk.description = form.description.data
        squawk.status = form.status.data
        squawk.resolution_notes = form.resolution_notes.data
        if form.status.data == 'resolved' and squawk.status != 'resolved':
            squawk.resolved_at = datetime.utcnow()
            squawk.resolved_by_id = current_user.id
        db.session.commit()
        flash('Squawk updated successfully.', 'success')
        return redirect(url_for('maintenance.aircraft_squawks', aircraft_id=squawk.aircraft_id))
    return render_template('maintenance/squawk_form.html', form=form, aircraft=squawk.aircraft, title='Edit Squawk') 