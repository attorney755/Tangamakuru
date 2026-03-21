from app import create_app, db
from app.models import Report, User
from datetime import datetime

app = create_app()

with app.app_context():
    print("Testing Report Model")
    print("=" * 60)
    
    # Count existing reports
    report_count = Report.query.count()
    print(f"Existing reports: {report_count}")
    
    if report_count == 0:
        # Get a user to associate with report
        user = User.query.filter_by(role='citizen').first()
        
        if user:
            # Create a test report
            report = Report(
                title="Test Theft Report",
                description="My phone was stolen at the market",
                category="theft",
                province="Kigali City",
                district="Gasabo",
                sector="Remera",
                cell="Gishushu",
                village="Amahoro",
                specific_location="Near Remera market",
                priority="high",
                user_id=user.id
            )
            
            # Generate report ID
            report.report_id = report.generate_report_id()
            
            db.session.add(report)
            db.session.commit()
            
            print(f"✅ Created test report: {report.report_id}")
            print(f"   Title: {report.title}")
            print(f"   Status: {report.status}")
            print(f"   Created by: {report.reporter.email}")
        else:
            print("❌ No citizen user found to create report")
    
    # Show all reports
    reports = Report.query.all()
    print(f"\nTotal reports in database: {len(reports)}")
    for r in reports:
        print(f"  - {r.report_id}: {r.title} ({r.status})")
    
    print("\n" + "=" * 60)