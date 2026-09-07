from app.processing import assigned_names


def test_extracts_assignment_team() -> None:
    assert assigned_names("Pasa los datos de Conejo para que vayan Wilson Carlos y Oscar") == ["Wilson", "Carlos", "Oscar"]
