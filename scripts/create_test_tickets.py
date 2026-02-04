"""Script to create test tickets for MediConnect product in Jira."""

from app.jira.fetcher import create_jira_ticket

# MediConnect - Patient Portal for Healthcare
# Mix of well-written and poorly-written tickets
# All using "Tarea" issue type (only available type in this project)

tickets = [
    # === WELL-WRITTEN TICKETS ===
    {
        'summary': '[Feature] Patient can schedule appointment with available doctors',
        'description': """## Description
As a patient, I want to schedule a new appointment with an available doctor so that I can receive medical care at a convenient time.

## Acceptance Criteria
- Patient can view list of available doctors by specialty
- Patient can see doctor's available time slots for the next 30 days
- Patient can select a time slot and confirm the appointment
- System sends confirmation email to patient
- Appointment appears in patient's dashboard

## Technical Notes
- Integrate with Google Calendar API for availability
- Send email via SendGrid
- Store appointment in PostgreSQL database"""
    },
    {
        'summary': '[Feature] Implement secure login with MFA for patient accounts',
        'description': """## Description
Implement multi-factor authentication (MFA) for patient login to enhance account security and comply with HIPAA requirements.

## Acceptance Criteria
- Patient can enable MFA from account settings
- Support for SMS and Authenticator app (TOTP)
- MFA is required after password entry
- Patient can set trusted devices (skip MFA for 30 days)
- Recovery codes available for backup access

## Security Requirements
- TOTP tokens valid for 30 seconds
- Rate limit: 5 failed attempts = 15 min lockout
- Audit log all MFA events"""
    },
    {
        'summary': '[Feature] Display prescription history with refill request option',
        'description': """## Description
Patients need to view their prescription history and request refills directly from the portal.

## Acceptance Criteria
- Show all prescriptions from the last 2 years
- Display: medication name, dosage, prescribing doctor, date, refills remaining
- Patient can request refill with one click
- Refill request sent to pharmacy and doctor for approval
- Show status of pending refill requests

## Out of Scope
- Controlled substances (require in-person visit)
- New prescriptions"""
    },
    {
        'summary': '[Bug] Appointment confirmation email not sent for same-day bookings',
        'description': """## Bug Description
When a patient books an appointment for the same day, the confirmation email is not being sent. This only affects same-day appointments; future appointments work correctly.

## Steps to Reproduce
1. Login as patient
2. Go to Schedule Appointment
3. Select today's date
4. Choose an available time slot
5. Confirm booking

## Expected Behavior
Confirmation email sent within 2 minutes of booking.

## Actual Behavior
No email received. Appointment does appear in dashboard.

## Environment
- Production
- Affects all browsers
- First reported: Jan 15, 2025"""
    },
    {
        'summary': '[Feature] Add patient profile photo upload functionality',
        'description': """## Description
Allow patients to upload a profile photo to personalize their account and help doctors identify them.

## Acceptance Criteria
- Support JPG, PNG formats
- Max file size: 5MB
- Image cropped to square (user can adjust)
- Photo displayed in header and appointment cards
- Default avatar if no photo uploaded

## Technical Notes
- Store in AWS S3
- Generate thumbnail (100x100) for performance
- Validate file type server-side"""
    },

    # === MEDIUM QUALITY TICKETS ===
    {
        'summary': '[Feature] Patient dashboard shows upcoming appointments',
        'description': """Show the patient their upcoming appointments on the main dashboard after login.

Should display:
- Date and time
- Doctor name
- Appointment type
- Location or video link

Add a "View All" button to see full appointment history."""
    },
    {
        'summary': '[Feature] Add search functionality for doctors',
        'description': """Patients should be able to search for doctors by:
- Name
- Specialty
- Location
- Insurance accepted

Results should show doctor photo, rating, and next available slot."""
    },
    {
        'summary': '[Feature] Email notifications for appointment reminders',
        'description': """Send reminder emails before appointments:
- 24 hours before
- 1 hour before

Include appointment details and option to reschedule or cancel."""
    },
    {
        'summary': '[Bug] Calendar shows wrong timezone for some users',
        'description': """Some users report that appointment times are displayed in the wrong timezone.

Seems to affect users who travel or have non-US timezones set on their devices.

Need to investigate and fix."""
    },
    {
        'summary': '[Feature] Patient can cancel appointment from portal',
        'description': """Allow patients to cancel appointments directly from the portal.

Rules:
- Can cancel up to 24 hours before appointment
- Less than 24 hours requires phone call
- Show cancellation policy before confirming

Send cancellation confirmation email."""
    },

    # === POORLY-WRITTEN TICKETS ===
    {
        'summary': 'fix the login thing',
        'description': """users cant login sometimes. need to fix asap"""
    },
    {
        'summary': 'add video call feature',
        'description': """we need video calls for telemedicine"""
    },
    {
        'summary': 'make it faster',
        'description': """the app is slow. make it faster please."""
    },
    {
        'summary': 'insurance stuff',
        'description': """need to handle insurance verification somehow"""
    },
    {
        'summary': 'mobile app',
        'description': """patients want mobile app. ios and android."""
    },
    {
        'summary': 'doctor notes',
        'description': """doctors should be able to add notes after appointments. patients can view them later."""
    },
    {
        'summary': 'something broken in prod',
        'description': """getting errors in production. check logs."""
    },
    {
        'summary': 'payment integration',
        'description': """add stripe for payments. copays and stuff."""
    },
    {
        'summary': 'URGENT: security issue',
        'description': """found security problem. need to fix. ask john for details."""
    },
    {
        'summary': '[Feature] Patient medical records access',
        'description': """## Description
Patients should be able to view their medical records including lab results, visit summaries, and imaging reports.

## Requirements
- View lab results with normal ranges highlighted
- Download visit summaries as PDF
- View imaging reports (no actual images, just reports)
- Filter by date range and record type

## Compliance
Must comply with HIPAA regulations for PHI access logging."""
    },
]


def main():
    print('Creating 20 test tickets for MediConnect project...')
    print('=' * 60)

    created = 0
    failed = 0

    for i, ticket in enumerate(tickets, 1):
        success, result = create_jira_ticket(
            project_key='PROREF',
            summary=ticket['summary'],
            description=ticket['description'],
            issue_type='Tarea'  # Only available type in this project
        )
        if success:
            print(f'{i:2}. [{result}] {ticket["summary"][:45]}...')
            created += 1
        else:
            print(f'{i:2}. ERROR: {result[:70]}')
            failed += 1

    print('=' * 60)
    print(f'Created: {created} | Failed: {failed}')


if __name__ == '__main__':
    main()

