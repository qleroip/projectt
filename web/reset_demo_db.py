from app import app, db, seed_data


with app.app_context():
    db.drop_all()
    db.create_all()
    seed_data()
    print("Demo database has been reset.")
