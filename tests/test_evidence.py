from app.services.ai import validate_evidence

def test_invalid_evidence_marks_scene_unsupported():
    result={"script":"A fact.","evidence":[{"id":"e1","quote":"not in source"}],"scenes":[{"id":"s1","evidence_ids":["e1"]}]}
    checked=validate_evidence(result,"The actual article text.")
    assert checked["evidence"]==[]
    assert any(item.get("scene_id")=="s1" for item in checked["unsupported_claims"])
