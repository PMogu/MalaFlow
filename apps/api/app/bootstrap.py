from sqlalchemy.orm import Session


def seed_demo_data(db: Session) -> None:
    """Intentionally empty.

    The experiment no longer ships test restaurants or accounts. Keep this
    import-compatible helper so old local scripts fail softly instead of
    recreating demo data.
    """
    db.commit()
