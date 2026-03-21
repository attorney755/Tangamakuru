from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    print("Checking and creating test users...")
    print("=" * 50)
    
    # Count existing users
    user_count = User.query.count()
    print(f"Existing users in database: {user_count}")
    
    if user_count == 0:
        print("\nCreating test users...")
        
        # Admin user
        admin = User(
            email="admin@tangamakuru.rw",
            first_name="System",
            last_name="Administrator",
            phone="0780000000",
            role="admin",
            province="Kigali City",
            district="Gasabo",
            is_active=True,
            is_verified=True
        )
        admin.set_password("Admin@2024")
        db.session.add(admin)
        
        # Sector Officer
        officer = User(
            email="officer@tangamakuru.rw",
            first_name="Sector",
            last_name="Officer",
            phone="0781111111",
            role="officer",
            province="Kigali City",
            district="Gasabo",
            sector="Remera",
            officer_id="OFF-001",
            department="Public Safety",
            is_active=True,
            is_verified=True
        )
        officer.set_password("Officer@2024")
        db.session.add(officer)
        
        # Citizen
        citizen = User(
            email="citizen@tangamakuru.rw",
            first_name="Test",
            last_name="Citizen",
            phone="0782222222",
            role="citizen",
            province="Kigali City",
            district="Gasabo",
            sector="Remera",
            cell="Gishushu",
            village="Amahoro",
            is_active=True,
            is_verified=True
        )
        citizen.set_password("Citizen@2024")
        db.session.add(citizen)
        
        db.session.commit()
        print("✅ Created 3 test users")
        
        # Display created users
        users = User.query.all()
        print("\nCreated users:")
        for user in users:
            print(f"  - {user.email} ({user.role}) - Password: {user.role.capitalize()}@2024")
    else:
        print("\n✅ Users already exist in database:")
        users = User.query.all()
        for user in users:
            print(f"  - {user.email} ({user.role}) - Created: {user.created_at}")
    
    print("\n" + "=" * 50)
    print("Test users ready!")
    print("\nLogin credentials:")
    print("  Admin:    admin@tangamakuru.rw / Admin@2024")
    print("  Officer:  officer@tangamakuru.rw / Officer@2024")
    print("  Citizen:  citizen@tangamakuru.rw / Citizen@2024")