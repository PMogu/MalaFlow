from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.commit()
        print("Schema ready. No demo restaurant or test account was created.")
        print("Open /admin/login and onboard a real pilot restaurant.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
