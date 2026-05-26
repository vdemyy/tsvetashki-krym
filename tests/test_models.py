"""Тесты для моделей БД."""

from datetime import date

from models import Phenomenon, Place, Event, Subscription


class TestModels:
    def test_create_phenomenon(self, db_session):
        ph = Phenomenon(
            slug="test-slug",
            name="Test Phenomenon",
            kind="flowering",
        )
        db_session.add(ph)
        db_session.commit()

        result = db_session.get(Phenomenon, ph.id)
        assert result is not None
        assert result.slug == "test-slug"
        assert result.kind == "flowering"

    def test_create_place(self, db_session):
        pl = Place(
            name="Test Place",
            region="Test Region",
            latitude=44.5,
            longitude=34.2,
        )
        db_session.add(pl)
        db_session.commit()

        assert pl.id is not None
        assert pl.name == "Test Place"

    def test_create_event_with_relations(self, db_session):
        ph = Phenomenon(slug="test", name="Test", kind="flowering")
        pl = Place(name="Place", latitude=44.5, longitude=34.2)
        db_session.add_all([ph, pl])
        db_session.flush()

        ev = Event(
            phenomenon_id=ph.id,
            place_id=pl.id,
            start_date=date(2026, 6, 1),
            peak_date=date(2026, 6, 15),
            end_date=date(2026, 6, 30),
            intensity=4,
        )
        db_session.add(ev)
        db_session.commit()

        assert ev.phenomenon.name == "Test"
        assert ev.place.name == "Place"

    def test_subscription_dedup(self, db_session):
        """UniqueConstraint should prevent duplicate email+phenomenon subscriptions."""
        ph = Phenomenon(slug="test", name="Test", kind="flowering")
        db_session.add(ph)
        db_session.flush()

        sub1 = Subscription(email="a@b.com", phenomenon_id=ph.id, active=True)
        db_session.add(sub1)
        db_session.commit()

        # Second subscription with same email+phenomenon should fail
        from sqlalchemy.exc import IntegrityError
        import pytest

        sub2 = Subscription(email="a@b.com", phenomenon_id=ph.id, active=True)
        db_session.add(sub2)
        with pytest.raises(IntegrityError):
            db_session.commit()
